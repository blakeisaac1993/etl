"""Load a meadow dataset and create a garden dataset."""

from owid.catalog import Table
from shared import add_metadata_vars

from etl.data_helpers import geo
from etl.helpers import PathFinder, create_dataset

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)

# Define poverty lines (dollar a day)
poverty_lines = [
    "190",
    "500",
    "1000",
    "3000",
]

# Define suffixes for smoothed variables
smooth_suffix = ["", "_smooth"]

# Define first and last year of the dataset
FIRST_YEAR = 1820
LAST_YEAR = 2018


def run(dest_dir: str) -> None:
    #
    # Load inputs.
    #
    # Load meadow dataset.
    ds_meadow = paths.load_dataset("moatsos_historical_poverty")

    # Read table from meadow dataset.
    tb = ds_meadow["moatsos_historical_poverty"].reset_index()

    #
    # Process data.

    # Smooth estimates to address uncertainty
    tb = smooth_estimates(tb, poverty_lines)

    # Create headcount, above and between poverty lines variables
    tb = create_above_and_between_vars(tb, poverty_lines, smooth_suffix)

    tb = geo.harmonize_countries(
        df=tb,
        countries_file=paths.country_mapping_path,
    )
    tb = tb.set_index(["country", "year"], verify_integrity=True)

    # Add metadata by code
    tb = add_metadata_vars(tb)

    #
    # Save outputs.
    #
    # Create a new garden dataset with the same metadata as the meadow dataset.
    ds_garden = create_dataset(
        dest_dir, tables=[tb], check_variables_metadata=True, default_metadata=ds_meadow.metadata
    )

    # Save changes in the new garden dataset.
    ds_garden.save()


def smooth_estimates(tb: Table, poverty_lines: list) -> Table:
    """
    Smooth estimates to address uncertainty
    """

    tb_smooth = tb.copy()

    # Sort by country and year
    tb_smooth = tb_smooth.sort_values(["country", "year"]).reset_index(drop=True)

    smooth_cols = []

    for povline in poverty_lines:
        # Calculate 10-year rolling averages per country
        tb_smooth[f"headcount_ratio_{povline}_smooth"] = tb_smooth.groupby("country")[
            f"headcount_ratio_{povline}"
        ].transform(lambda x: x.rolling(10, 1).mean())
        smooth_cols.append(f"headcount_ratio_{povline}_smooth")

        # Replace values in LAST_YEAR with original values
        tb_smooth.loc[tb_smooth["year"] == LAST_YEAR, f"headcount_ratio_{povline}_smooth"] = tb_smooth.loc[
            tb_smooth["year"] == LAST_YEAR, f"headcount_ratio_{povline}"
        ].values

    # For CBN
    tb_smooth["headcount_ratio_cbn_smooth"] = tb_smooth.groupby("country")["headcount_ratio_cbn"].transform(
        lambda x: x.rolling(10, 1).mean()
    )
    smooth_cols.append("headcount_ratio_cbn_smooth")

    # Replace values in LAST_YEAR with original values
    tb_smooth.loc[tb_smooth["year"] == LAST_YEAR, "headcount_ratio_cbn_smooth"] = tb_smooth.loc[
        tb_smooth["year"] == LAST_YEAR, "headcount_ratio_cbn"
    ].values

    # Select decadal years, FIRST_YEAR and LAST_YEAR
    tb_smooth = tb_smooth[
        (tb_smooth["year"] % 10 == 0) | (tb_smooth["year"] == FIRST_YEAR) | (tb_smooth["year"] == LAST_YEAR)
    ].reset_index(drop=True)

    # Merge with tb

    tb = tb.merge(tb_smooth[["country", "year"] + smooth_cols], on=["country", "year"], how="left")

    return tb


def create_above_and_between_vars(tb: Table, poverty_lines: list, smooth_suffix: list) -> Table:
    """
    Create additional variables from the share and number in poverty: above and between poverty lines (or CBN).
    Also, add metadata to these variables.
    """
    # Add population column to estimate other variables
    tb["pop"] = tb["headcount_cbn"] / (tb["headcount_ratio_cbn"] / 100)
    tb["pop"] = tb["pop"].astype(float)

    # Create headcount_cbn_smooth
    tb["headcount_cbn_smooth"] = tb["headcount_ratio_cbn_smooth"] * tb["pop"] / 100

    # Create additional variables
    # Define columns to use

    cols_number = ["headcount_cbn", "headcount_cbn_smooth"]
    cols_above = []
    cols_number_above = []
    cols_between = []
    cols_number_between = []

    for smooth in smooth_suffix:
        for povline in poverty_lines:
            tb[f"headcount_{povline}{smooth}"] = tb[f"headcount_ratio_{povline}{smooth}"] * tb["pop"] / 100
            cols_number.append(f"headcount_{povline}{smooth}")

        # Share and number of people above poverty lines
        for povline in poverty_lines:
            tb[f"headcount_ratio_above_{povline}{smooth}"] = 100 - tb[f"headcount_ratio_{povline}{smooth}"]
            cols_above.append(f"headcount_ratio_above_{povline}{smooth}")
            tb[f"headcount_above_{povline}{smooth}"] = tb[f"headcount_ratio_above_{povline}{smooth}"] * tb["pop"] / 100
            cols_number_above.append(f"headcount_above_{povline}{smooth}")

        # Also do it for cbn
        tb[f"headcount_ratio_above_cbn{smooth}"] = 100 - tb[f"headcount_ratio_cbn{smooth}"]
        cols_above.append(f"headcount_ratio_above_cbn{smooth}")
        tb[f"headcount_above_cbn{smooth}"] = tb[f"headcount_ratio_above_cbn{smooth}"] * tb["pop"] / 100
        cols_number_above.append(f"headcount_above_cbn{smooth}")

        # Share and number of people in between poverty lines (World Bank)
        # For each poverty line in cols_wb
        for i in range(len(poverty_lines)):
            if i != 0:
                tb[f"headcount_ratio_between_{poverty_lines[i-1]}_{poverty_lines[i]}{smooth}"] = (
                    tb[f"headcount_ratio_{poverty_lines[i]}"] - tb[f"headcount_ratio_{poverty_lines[i-1]}{smooth}"]
                )
                cols_between.append(f"headcount_ratio_between_{poverty_lines[i-1]}_{poverty_lines[i]}{smooth}")

                tb[f"headcount_between_{poverty_lines[i-1]}_{poverty_lines[i]}{smooth}"] = (
                    tb[f"headcount_ratio_between_{poverty_lines[i-1]}_{poverty_lines[i]}{smooth}"] * tb["pop"] / 100
                )
                cols_number_between.append(f"headcount_between_{poverty_lines[i-1]}_{poverty_lines[i]}{smooth}")

    # Round to integer numbers
    tb[cols_number + cols_number_above + cols_number_between] = tb[
        cols_number + cols_number_above + cols_number_between
    ].round()

    # Remove pop column
    tb = tb.drop(columns=["pop"])

    return tb
