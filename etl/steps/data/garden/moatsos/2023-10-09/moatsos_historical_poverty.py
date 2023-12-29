"""Load a meadow dataset and create a garden dataset."""

from shared import add_metadata_vars

from etl.data_helpers import geo
from etl.helpers import PathFinder, create_dataset

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)


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
    #
    # Add population column to estimate other variables
    tb["pop"] = tb["headcount_cbn"] / (tb["headcount_ratio_cbn"] / 100)
    # -

    # Create additional variables
    # Define columns to use

    poverty_lines = [
        "190",
        "500",
        "1000",
        "3000",
    ]
    cols_number = ["headcount_cbn"]
    cols_above = []
    cols_number_above = []
    cols_between = []
    cols_number_between = []

    for povline in poverty_lines:
        tb[f"headcount_{povline}"] = tb[f"headcount_ratio_{povline}"] * tb["pop"] / 100
        cols_number.append(f"headcount_{povline}")

    # Share of people above poverty lines
    for povline in poverty_lines:
        tb[f"headcount_ratio_above_{povline}"] = 100 - tb[f"headcount_ratio_{povline}"]
        cols_above.append(f"headcount_ratio_above_{povline}")
        tb[f"headcount_above_{povline}"] = tb[f"headcount_ratio_above_{povline}"] * tb["pop"] / 100
        cols_number_above.append(f"headcount_above_{povline}")

    # Also do it for cbn
    tb["headcount_ratio_above_cbn"] = 100 - tb["headcount_ratio_cbn"]
    cols_above.append("headcount_ratio_above_cbn")
    tb["headcount_above_cbn"] = tb["headcount_ratio_above_cbn"] * tb["pop"] / 100
    cols_number_above.append("headcount_above_cbn")

    # Share of people in between poverty lines (World Bank)
    # For each poverty line in cols_wb
    for i in range(len(poverty_lines)):
        if i != 0:
            tb[f"headcount_ratio_between_{poverty_lines[i-1]}_{poverty_lines[i]}"] = (
                tb[f"headcount_ratio_{poverty_lines[i]}"] - tb[f"headcount_ratio_{poverty_lines[i-1]}"]
            )
            cols_between.append(f"headcount_ratio_between_{poverty_lines[i-1]}_{poverty_lines[i]}")

            tb[f"headcount_between_{poverty_lines[i-1]}_{poverty_lines[i]}"] = (
                tb[f"headcount_ratio_between_{poverty_lines[i-1]}_{poverty_lines[i]}"] * tb["pop"] / 100
            )
            cols_number_between.append(f"headcount_between_{poverty_lines[i-1]}_{poverty_lines[i]}")

    # Round to integer numbers
    tb[cols_number + cols_number_above + cols_number_between] = tb[
        cols_number + cols_number_above + cols_number_between
    ].round()

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
