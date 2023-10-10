"""Load a snapshot and create a meadow dataset."""

from functools import reduce

import owid.catalog.processing as pr

from etl.helpers import PathFinder, create_dataset

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)


def run(dest_dir: str) -> None:
    #
    # Load inputs.
    #
    # Retrieve snapshot and load data
    # OECD (Cost of Basic Needs and $1.90 poverty line (2011 PPP))
    snap = paths.load_snapshot("moatsos_historical_poverty_oecd.csv")
    tb_oecd = snap.read()

    # $5, $10, $30 poverty lines (2011 PPP)
    snap = paths.load_snapshot("moatsos_historical_poverty_5.csv")
    tb_5 = snap.read()

    snap = paths.load_snapshot("moatsos_historical_poverty_10.csv")
    tb_10 = snap.read()

    snap = paths.load_snapshot("moatsos_historical_poverty_30.csv")
    tb_30 = snap.read()

    # Multiple merge
    tables = [tb_oecd, tb_5, tb_10, tb_30]
    tb = reduce(lambda left, right: pr.merge(left, right, on=["Region", "Year"], how="outer"), tables)

    # Rename columns

    tb = tb.rename(
        columns={
            "Region": "country",
            "Year": "year",
            "PovRate": "headcount_ratio_cbn",
            "PovRate1.9": "headcount_ratio_190",
            "PovRateAt5DAD": "headcount_ratio_500",
            "PovRateAt10DAD": "headcount_ratio_1000",
            "PovRateAt30DAD": "headcount_ratio_3000",
        }
    )
    # Keep data only up to 2018
    tb = tb[tb["year"] <= 2018].reset_index(drop=True)

    # Select columns and multiply by 100 (also keep a list of World Bank poverty method variables)
    cols = [
        "headcount_ratio_cbn",
        "headcount_ratio_190",
        "headcount_ratio_500",
        "headcount_ratio_1000",
        "headcount_ratio_3000",
    ]

    tb[cols] *= 100

    # Obtain CBN share for countries
    snap = paths.load_snapshot("moatsos_historical_poverty_oecd_countries_share.xlsx")
    tb_cbn_share = snap.read(sheet_name="Sheet1", header=2)

    tb_cbn_share = pr.melt(tb_cbn_share, id_vars=["Year"], var_name="country", value_name="headcount_ratio_cbn")
    tb_cbn_share = tb_cbn_share.rename(columns={"Year": "year"})

    tb = pr.concat([tb, tb_cbn_share], ignore_index=True)

    # Obtain CBN number for regions
    snap = paths.load_snapshot("moatsos_historical_poverty_oecd_regions_number.xlsx")
    tb_cbn_number = snap.read(sheet_name="g9-4", header=17)

    # Drop and rename columns to adapt the format
    tb_cbn_number = tb_cbn_number.drop(columns=["Total1820"])
    tb_cbn_number = tb_cbn_number.rename(columns={"Unnamed: 0": "year"})

    # Transform numbers from millions
    tb_cbn_number.iloc[:, 1:] = tb_cbn_number.iloc[:, 1:] * 1000000

    # Calculate a World total from the regions
    tb_cbn_number["World"] = tb_cbn_number.iloc[:, 1:].sum(1)

    tb_cbn_number = pr.melt(tb_cbn_number, id_vars=["year"], var_name="country", value_name="headcount_cbn")
    tb_cbn_number["headcount_cbn"] = tb_cbn_number["headcount_cbn"].round(0).astype(int)

    # Merge with the main table
    tb = pr.merge(tb, tb_cbn_number, on=["country", "year"], how="left", short_name="moatsos_historical_poverty")

    # Merge all the tables

    #
    # Process data.
    #
    # Ensure all columns are snake-case, set an appropriate index, and sort conveniently.
    tb = tb.underscore().set_index(["country", "year"], verify_integrity=True).sort_index()

    #
    # Save outputs.
    #
    # Create a new meadow dataset with the same metadata as the snapshot.
    ds_meadow = create_dataset(dest_dir, tables=[tb], check_variables_metadata=True, default_metadata=snap.metadata)

    # Save changes in the new meadow dataset.
    ds_meadow.save()
