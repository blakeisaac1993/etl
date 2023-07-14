import datetime as dt

import pandas as pd
import pytz
from owid.catalog import Table
from structlog import get_logger

from etl.helpers import PathFinder, create_dataset

log = get_logger()

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)


def run(dest_dir: str) -> None:
    #
    # Load data from github.
    #
    deps = [dep for dep in paths.dependencies if dep.startswith("etag://")]
    assert len(deps) == 1
    url = deps[0].replace("etag://", "https://")

    df = (
        pd.read_csv(url)
        .rename(columns={"Year": "year", "Country": "country"})
        .set_index(["year", "country"])
        .dropna(axis=0, how="all")
    )

    #
    # Process data.
    #
    # Create a new table and ensure all columns are snake-case.
    tb = Table(df, short_name=paths.short_name, underscore=True)

    #
    # Save outputs.
    #
    # Create a new garden dataset with the same metadata as the snapshot.
    ds_garden = create_dataset(dest_dir, tables=[tb])

    # Add Last updated to source.
    ds_garden.sources[0].name = f"Google COVID-19 Community Mobility Trends - Last updated {time_str_grapher()}"

    # Save changes in the new garden dataset.
    ds_garden.save()


def time_str_grapher():
    return (
        (dt.datetime.now() - dt.timedelta(minutes=10)).astimezone(pytz.timezone("Europe/London")).strftime("%-d %B %Y")
    )