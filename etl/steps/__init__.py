#
#  __init__.py
#  steps
#

from typing import Protocol, List, cast
from pathlib import Path
import hashlib
import tempfile
from dataclasses import dataclass
from glob import glob
from importlib import import_module
import warnings

# smother deprecation warnings by papermill
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import papermill as pm

from owid import catalog
from owid import walden

from etl import files
from etl import paths


class Step(Protocol):
    path: str

    def run(self) -> None:
        ...

    def is_dirty(self) -> bool:
        ...

    def checksum_output(self) -> str:
        ...


class DataStep(Step):
    """
    A step which creates a local Dataset on disk in the data/ folder. You specify it
    by making a Python module or a Jupyter notebook with a matching path in the
    etl/steps/data folder.
    """

    path: str
    dependencies: List[Step]

    def __init__(self, path: str, dependencies: List[Step]) -> None:
        self.path = path
        self.dependencies = dependencies

    def __str__(self) -> str:
        return f"data://{self.path}"

    def run(self) -> None:
        # make sure the encosing folder is there
        self._dest_dir.parent.mkdir(parents=True, exist_ok=True)

        sp = self._search_path
        if sp.with_suffix(".py").exists() or (sp / "__init__.py").exists():
            self._run_py()

        elif sp.with_suffix(".ipynb").exists():
            self._run_notebook()

        else:
            raise Exception(f"have no idea how to run step: {self.path}")

        # modify the dataset to remember what inputs were used to build it
        dataset = self._output_dataset
        dataset.metadata.source_checksum = self.checksum_input()
        dataset.save()

    def is_reference(self) -> bool:
        return self.path == "reference"

    def is_dirty(self) -> bool:
        # the reference dataset never needs rebuilding
        if self.is_reference():
            return False

        if not self._dest_dir.is_dir() or any(
            isinstance(d, DataStep) and not d.has_existing_data()
            for d in self.dependencies
        ):
            return True

        found_source_checksum = catalog.Dataset(
            self._dest_dir.as_posix()
        ).metadata.source_checksum
        exp_source_checksum = self.checksum_input()

        if found_source_checksum != exp_source_checksum:
            return True

        return False

    def has_existing_data(self) -> bool:
        return self._dest_dir.is_dir()

    def can_execute(self) -> bool:
        sp = self._search_path
        return (
            # python script
            sp.with_suffix(".py").exists()
            # folder of scripts with __init__.py
            or (sp / "__init__.py").exists()
            # jupyter notebook
            or sp.with_suffix(".ipynb").exists()
        )

    def checksum_input(self) -> str:
        "Return the MD5 of all ingredients for making this step."
        checksums = {}
        for d in self.dependencies:
            checksums[d.path] = d.checksum_output()

        for f in self._step_files():
            checksums[f] = files.checksum_file(f)

        in_order = [v for _, v in sorted(checksums.items())]
        return hashlib.md5(",".join(in_order).encode("utf8")).hexdigest()

    @property
    def _output_dataset(self) -> catalog.Dataset:
        "If this step is completed, return the MD5 of the output."
        if not self._dest_dir.is_dir():
            raise Exception("dataset has not been created yet")

        return catalog.Dataset(self._dest_dir.as_posix())

    def checksum_output(self) -> str:
        # This cast from str to str is IMHO unnecessary but MyPy complains about this without it...
        return cast(str, self._output_dataset.checksum())

    def _step_files(self) -> List[str]:
        "Return a list of code files defining this step."
        if self._search_path.is_dir():
            return [p.as_posix() for p in files.walk(self._search_path)]

        return glob(self._search_path.as_posix() + ".*")

    @property
    def _search_path(self) -> Path:
        return paths.STEP_DIR / "data" / self.path

    @property
    def _dest_dir(self) -> Path:
        return paths.DATA_DIR / self.path.lstrip("/")

    def _run_py(self) -> None:
        """
        Import the Python module for this step and call run() on it.
        """
        module_path = self.path.lstrip("/").replace("/", ".")
        step_module = import_module(f"etl.steps.data.{module_path}")
        if not hasattr(step_module, "run"):
            raise Exception(f'no run() method defined for module "{step_module}"')

        # data steps
        step_module.run(self._dest_dir.as_posix())  # type: ignore

    def _run_notebook(self) -> None:
        "Run a parameterised Jupyter notebook."
        notebook_path = self._search_path.with_suffix(".ipynb")
        with tempfile.TemporaryDirectory() as tmp_dir:
            notebook_out = Path(tmp_dir) / "notebook.ipynb"
            log_file = Path(tmp_dir) / "output.log"
            with open(log_file.as_posix(), "w") as ostream:
                pm.execute_notebook(
                    notebook_path.as_posix(),
                    notebook_out.as_posix(),
                    parameters={"dest_dir": self._dest_dir.as_posix()},
                    progress_bar=False,
                    stdout_file=ostream,
                    stderr_file=ostream,
                )


@dataclass
class WaldenStep(Step):
    path: str

    def __init__(self, path: str) -> None:
        self.path = path

    def __str__(self) -> str:
        return f"walden://{self.path}"

    def run(self) -> None:
        "Ensure the dataset we're looking for is there."
        self._walden_dataset.ensure_downloaded(quiet=True)

    def is_dirty(self) -> bool:
        return not Path(self._walden_dataset.local_path).exists()

    def has_existing_data(self) -> bool:
        return True

    def checksum_output(self) -> str:
        checksum: str = cast(str, self._walden_dataset.md5)
        if not checksum:
            raise Exception(
                f"no md5 checksum available for walden dataset: {self.path}"
            )
        return checksum

    @property
    def _walden_dataset(self) -> walden.Dataset:
        if self.path.count("/") != 2:
            raise ValueError(f"malformed walden path: {self.path}")

        namespace, version, short_name = self.path.split("/")
        catalog = walden.Catalog()

        # normally version is a year or date, but we also accept "latest"
        if version == "latest":
            dataset = catalog.find_latest(namespace=namespace, short_name=short_name)
        else:
            dataset = catalog.find_one(
                namespace=namespace, version=version, short_name=short_name
            )

        return dataset


class GithubStep(Step):
    pass
