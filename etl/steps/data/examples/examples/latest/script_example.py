from typing import cast

import pandas as pd
from owid.catalog import Dataset, Table

from etl.paths import DATA_DIR, REFERENCE_DATASET
from etl.snapshot import Snapshot


def load_wb_income() -> pd.DataFrame:
    """Load WB income groups dataset from walden."""
    snap = Snapshot("wb/2021-07-01/wb_income.xlsx")
    local_path = snap.path
    return cast(pd.DataFrame, pd.read_excel(local_path))


def run(dest_dir: str) -> None:
    df = load_wb_income()

    # Convert iso codes to country names
    reference_dataset = Dataset(REFERENCE_DATASET)
    countries_regions = reference_dataset["countries_regions"]
    df["country"] = df.Code.map(countries_regions.name)

    # NOTE: For simplicity we are loading population from Maddison, but in practive
    # you would load it from `garden/owid/latest/key_indicators`, i.e.
    # indicators = Dataset(DATA_DIR / "garden/owid/latest/key_indicators")
    # population = indicators["population"]["population"].xs(2022, level="year")

    # Add population
    maddison = Dataset(DATA_DIR / "garden/ggdc/2020-10-01/ggdc_maddison")
    population = maddison["maddison_gdp"]["population"].xs(2018, level="year")
    df["population"] = df.country.map(population)

    df = df.reset_index().rename(
        columns={
            "Income group": "income_group",
        }
    )
    df = df[["country", "population", "income_group"]]

    ds = Dataset.create_empty(dest_dir)
    ds.metadata.short_name = "dataset_example"
    ds.metadata.namespace = "examples"

    t = Table(df.reset_index(drop=True))
    t.metadata.short_name = "table_example"

    ds.add(t)
    ds.save()
