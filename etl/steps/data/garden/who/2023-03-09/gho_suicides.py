"""Load a meadow dataset and create a garden dataset.

Minor cleaning of GHO dataset (only age-standardized suicide rates metrics)"""

import pandas as pd
from owid.catalog import Dataset, Table
from structlog import get_logger

from etl.data_helpers import geo
from etl.helpers import PathFinder, create_dataset

log = get_logger()

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)


COLUMNS_RENAME = {
    "spatialdim": "country",
    "timedim": "year",
    "dim1": "sex",
    "numericvalue": "suicide_rate",
}
SEX_MAPPING = {
    "BTSX": "both sexes",
    "FMLE": "female",
    "MLE": "male",
}


def run(dest_dir: str) -> None:
    log.info("gho_suicides: start")

    #
    # Load inputs.
    #
    # Load meadow dataset.
    ds_meadow: Dataset = paths.load_dependency("gho_suicides")

    # Read table from meadow dataset.
    tb_meadow = ds_meadow["gho_suicides"]

    # Create a dataframe with data from the table.
    df = pd.DataFrame(tb_meadow)

    #
    # Process data.
    #
    log.info("gho_suicides.harmonize_countries")
    df = process(df)

    # Create a new table with the processed data.
    tb_garden = Table(df, short_name=ds_meadow.metadata.short_name)

    #
    # Save outputs.
    #
    # Create a new garden dataset with the same metadata as the meadow dataset.
    ds_garden = create_dataset(dest_dir, tables=[tb_garden], default_metadata=ds_meadow.metadata)
    ds_garden.update_metadata(paths.metadata_path)
    # Save changes in the new garden dataset.
    ds_garden.save()

    log.info("gho_suicides.end")


def process(df: pd.DataFrame) -> pd.DataFrame:
    # Rename columns
    log.info("gho_suicides: rename column names")
    df = df[COLUMNS_RENAME.keys()].rename(columns=COLUMNS_RENAME)

    # Harmonize countries
    log.info("gho_suicides: harmonize countries")
    df = geo.harmonize_countries(
        df=df,
        countries_file=paths.country_mapping_path,
    )
    # Harmonize sex groups
    log.info("gho_suicides: harmonize sex")
    df["sex"] = df["sex"].map(SEX_MAPPING)

    # Sort rows and set index
    log.info("gho_suicides: sorting rows and setting index")
    columns_idx = ["country", "year", "sex"]
    df = df.sort_values(columns_idx).set_index(columns_idx)

    return df
