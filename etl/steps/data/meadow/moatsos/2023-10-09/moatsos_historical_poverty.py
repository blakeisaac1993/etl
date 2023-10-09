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
    tb = tb.rename(
        columns={
            "Region": "country",
            "PovRate": "headcount_ratio_cbn",
            "PovRate1.9": "headcount_ratio_190",
            "PovRateAt5DAD": "headcount_ratio_500",
            "PovRateAt10DAD": "headcount_ratio_1000",
            "PovRateAt30DAD": "headcount_ratio_3000",
        }
    )
    # Keep data only up to 2018
    tb = tb[tb["Year"] <= 2018].reset_index(drop=True)

    # Select columns and multiply by 100 (also keep a list of World Bank poverty method variables)
    cols = [
        "headcount_ratio_cbn",
        "headcount_ratio_190",
        "headcount_ratio_500",
        "headcount_ratio_1000",
        "headcount_ratio_3000",
    ]
    cols_wb = ["headcount_ratio_190", "headcount_ratio_500", "headcount_ratio_1000", "headcount_ratio_3000"]

    tb[cols] *= 100

    # Obtain CBN share for countries and number for regions
    snap = paths.load_snapshot("moatsos_historical_poverty_oecd_countries_share.csv")
    tb_cbn_share = snap.read(sheet_name="Sheet1", header=2)

    snap = paths.load_snapshot("moatsos_historical_poverty_oecd_regions_number.csv")
    tb_cbn_number = snap.read(sheet_name="g9-4", header=17)

    tb_cbn_share = pr.melt(tb_cbn_share, id_vars=["Year"], var_name="country", value_name="headcount_ratio_cbn")

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
