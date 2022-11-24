import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Union

import yaml
from dataclasses_json import dataclass_json
from dvc.repo import Repo
from owid.catalog.meta import pruned_json
from owid.walden import files

from etl import paths

dvc = Repo(paths.BASE_DIR)


@dataclass
class Snapshot:

    uri: str
    metadata: "SnapshotMeta"

    def __init__(self, uri: str) -> None:
        """
        :param uri: URI of the snapshot file, typically `namespace/version/short_name.ext`
        """
        self.uri = uri

        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata file {self.metadata_path} not found")

        self.metadata = SnapshotMeta.load_from_yaml(self.metadata_path)

    @property
    def path(self) -> Path:
        """Path to materialized file."""
        return paths.DATA_DIR / "snapshots" / self.uri

    @property
    def metadata_path(self) -> Path:
        """Path to metadata file."""
        return Path(f"{paths.SNAPSHOTS_DIR / self.uri}.dvc")

    def pull(self) -> None:
        """Pull file from S3."""
        dvc.pull(str(self.path), remote=self._dvc_remote)

    def download_from_source(self) -> None:
        """Download file from source_data_url."""
        assert self.metadata.source_data_url, "source_data_url is not set"
        self.path.parent.mkdir(exist_ok=True, parents=True)
        files.download(self.metadata.source_data_url, str(self.path))

    def dvc_add(self, upload: bool) -> None:
        """Add file to DVC and upload to S3."""
        dvc.add(str(self.path), fname=str(self.metadata_path))
        if upload:
            dvc.push(str(self.path), remote=self._dvc_remote)

    @property
    def _dvc_remote(self):
        return "public" if self.metadata.is_public else "private"


@pruned_json
@dataclass_json
@dataclass
class SnapshotMeta:

    # how we identify the dataset
    namespace: str  # a short source name (usually institution name)
    short_name: str  # a slug, ideally unique, snake_case, no spaces

    # fields that are meant to be shown to humans
    name: str
    description: str
    source_name: str
    url: str

    # how to get the data file
    file_extension: str

    # today by default
    date_accessed: str = dt.datetime.now().date().strftime("%Y-%m-%d")

    # URL with file, use `download_and_create(metadata)` for uploading to walden
    source_data_url: Optional[str] = None

    # license
    # NOTE: license_url should be ideally required, but we don't have it for backported datasets
    # so we have to relax this condition
    license_url: Optional[str] = None
    license_name: Optional[str] = None
    access_notes: Optional[str] = None

    is_public: Optional[bool] = True

    # use either publication_year or publication_date as dataset version if not given explicitly
    version: Optional[str] = None
    publication_year: Optional[int] = None
    publication_date: Union[Optional[dt.date], Literal["latest"]] = None

    def __post_init__(self) -> None:
        if self.version is None:
            if self.publication_date:
                self.version = str(self.publication_date)
            elif self.publication_year:
                self.version = str(self.publication_year)
            else:
                raise ValueError("no versioning field found")
        else:
            # version can be loaded as datetime.date, but it has to be string
            self.version = str(self.version)

    @classmethod
    def load_from_yaml(cls, filename: Union[str, Path]) -> "SnapshotMeta":
        """Load metadata from YAML file. Metadata must be stored under `meta` key."""
        with open(filename) as istream:
            yml = yaml.safe_load(istream)
            if "meta" not in yml:
                raise ValueError("Metadata YAML should be stored under `meta` key")
            return cls.from_dict(yml["meta"])

    def to_dict(self) -> Dict[str, Any]:
        ...

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SnapshotMeta":
        ...
