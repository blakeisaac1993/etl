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
    ds_meadow = paths.load_dataset("worldwide_bureaucracy_indicators")

    # Read table from meadow dataset.
    tb = ds_meadow["worldwide_bureaucracy_indicators"].reset_index()

    #
    # Process data.

    # Rename columns
    tb = tb.rename(columns={"country_name": "country"})

    # Make indicator_code snake_case
    tb["indicator_code"] = tb["indicator_code"].str.lower().str.replace(".", "_", regex=False)

    # Save a dictionary with the unique values of the indicator_code and the corresponding indicator_name
    indicator_dict = (
        tb[["indicator_code", "indicator_name"]]
        .drop_duplicates()
        .set_index("indicator_code")
        .to_dict()["indicator_name"]
    )

    # Drop columns
    tb = tb.drop(columns=["country_code", "indicator_name"])

    # Drop column containing the text "unnamed"
    tb = tb.drop(columns=tb.filter(regex="unnamed").columns)

    # Make the table long
    tb = tb.melt(id_vars=["country", "indicator_code"], var_name="year", value_name="value")

    # Make table wide again, with the indicator_code as columns
    tb = tb.pivot(index=["country", "year"], columns="indicator_code", values="value").reset_index()

    # Remove trailing _ from year values
    tb["year"] = tb["year"].str.replace("_", "").astype(int)

    tb = geo.harmonize_countries(
        df=tb,
        countries_file=paths.country_mapping_path,
    )
    tb = tb.set_index(["country", "year"], verify_integrity=True)

    #
    # Save outputs.
    #
    # Add indicator.title with dictionary
    for col in indicator_dict:
        meta_title = indicator_dict[col]
        tb[col].metadata.title = meta_title

    # Create a new garden dataset with the same metadata as the meadow dataset.
    ds_garden = create_dataset(
        dest_dir, tables=[tb], check_variables_metadata=True, default_metadata=ds_meadow.metadata
    )

    # Save changes in the new garden dataset.
    ds_garden.save()
