"""Load a meadow dataset and create a garden dataset."""

from etl.data_helpers import geo
from etl.helpers import PathFinder, create_dataset

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)


def run(dest_dir: str) -> None:
    #
    # Load inputs.
    #
    # Load meadow dataset.
    ds_meadow = paths.load_dataset("cow_ssm")

    # Read table from meadow dataset.
    tb_system = ds_meadow["cow_ssm_system"].reset_index()
    tb_states = ds_meadow["cow_ssm_states"].reset_index()
    tb_majors = ds_meadow["cow_ssm_majors"].reset_index()

    #
    # Process data.
    #
    # Checks
    assert tb_system.groupby("ccode")["stateabb"].nunique().max() == 1, "Multiple `stateabb` values for same `ccode`"
    assert tb_states.groupby("ccode")["statenme"].nunique().max() == 1, "Multiple `statenme` values for same `ccode`"
    assert tb_majors.groupby("ccode")["stateabb"].nunique().max() == 1, "Multiple `stateabb` values for same `ccode`"

    # Add COW state names to those missing them
    tb_codes = tb_states[["stateabb", "statenme"]].drop_duplicates()
    ## tb_system
    length_first = tb_system.shape[0]
    tb_system = tb_system.merge(tb_codes, on="stateabb")
    assert tb_system.shape[0] == length_first, "Some `state_name` values are missing after merge (tb_system)!"
    ## tb_majors
    length_first = tb_majors.shape[0]
    tb_majors = tb_majors.merge(tb_codes, on="stateabb")
    assert tb_majors.shape[0] == length_first, "Some `state_name` values are missing after merge (tb_majors)!"

    # Harmonize country names
    tb_system = geo.harmonize_countries(df=tb_system, countries_file=paths.country_mapping_path, country_col="statenme")
    tb_states = geo.harmonize_countries(df=tb_states, countries_file=paths.country_mapping_path, country_col="statenme")
    tb_majors = geo.harmonize_countries(df=tb_majors, countries_file=paths.country_mapping_path, country_col="statenme")

    # Group tables and format tables
    tables = [
        tb_system.set_index(["ccode", "year"], verify_integrity=True).sort_index(),
        tb_states.set_index(["ccode", "styear", "stmonth", "stday", "endyear", "endmonth", "endday"]).sort_index(),
        tb_majors.set_index(["ccode", "styear", "stmonth", "stday", "endyear", "endmonth", "endday"]).sort_index(),
    ]

    # tb = tb.set_index(["country", "year"], verify_integrity=True)

    #
    # Save outputs.
    #
    # Create a new garden dataset with the same metadata as the meadow dataset.
    ds_garden = create_dataset(
        dest_dir, tables=tables, check_variables_metadata=True, default_metadata=ds_meadow.metadata
    )

    # Save changes in the new garden dataset.
    ds_garden.save()