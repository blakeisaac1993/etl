"""Load a meadow dataset and create a garden dataset."""

from typing import List, cast

import pandas as pd
from owid.catalog import Dataset, Table
from owid.catalog.utils import underscore

from etl.data_helpers import geo
from etl.helpers import PathFinder, create_dataset

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)
REGIONS = [
    "North America",
    "South America",
    "Europe",
    "European Union (27)",
    "Africa",
    "Asia",
    "Oceania",
    "Low-income countries",
    "Upper-middle-income countries",
    "Lower-middle-income countries",
    "High-income countries",
    "World",
]


def add_data_for_regions(tb: Table, regions: List[str], ds_regions: Dataset, ds_income_groups: Dataset) -> Table:
    tb_with_regions = tb.copy()
    aggregations = {column: "median" for column in tb_with_regions.columns if column not in ["country", "year"]}

    for region in REGIONS:
        # Find members of current region.
        members = geo.list_members_of_region(
            region=region,
            ds_regions=ds_regions,
            ds_income_groups=ds_income_groups,
        )
        tb_with_regions = geo.add_region_aggregates(
            df=tb_with_regions,
            region=region,
            countries_in_region=members,
            countries_that_must_have_data=[],
            num_allowed_nans_per_year=None,
            frac_allowed_nans_per_year=0.99999,
            aggregations=aggregations,
        )
    tb_with_regions = tb_with_regions.copy_metadata(from_table=tb)

    return tb_with_regions


def run(dest_dir: str) -> None:
    #
    # Load inputs.
    #
    # Load meadow dataset.
    ds_meadow = cast(Dataset, paths.load_dependency("education_lee_lee"))

    # Extract World Bank Education Dataset
    ds_garden_wb = cast(Dataset, paths.load_dependency("education"))
    tb_wb = ds_garden_wb["education"]

    # Extract indicators with enrolment rates from World Bank that match the ones in the current dataset (net enrolment up to secondary and gross enrolment for tertiary)
    select_enrolment_cols = [
        "total_net_enrolment_rate__primary__both_sexes__pct",
        "total_net_enrolment_rate__primary__female__pct",
        "total_net_enrolment_rate__primary__male__pct",
        "school_enrollment__tertiary__pct_gross",
        "school_enrollment__tertiary__female__pct_gross",
        "school_enrollment__tertiary__male__pct_gross",
        "total_net_enrolment_rate__lower_secondary__both_sexes__pct",
        "total_net_enrolment_rate__upper_secondary__both_sexes__pct",
        "total_net_enrolment_rate__lower_secondary__male__pct",
        "total_net_enrolment_rate__upper_secondary__male__pct",
        "total_net_enrolment_rate__lower_secondary__female__pct",
        "total_net_enrolment_rate__upper_secondary__female__pct",
    ]

    dictionary_to_rename_and_combine = {
        "total_net_enrolment_rate__primary__both_sexes__pct": "mf_primary_enrollment_rates",
        "total_net_enrolment_rate__primary__female__pct": "f_primary_enrollment_rates",
        "total_net_enrolment_rate__primary__male__pct": "m_primary_enrollment_rates",
        "school_enrollment__tertiary__pct_gross": "mf_tertiary_enrollment_rates",
        "school_enrollment__tertiary__female__pct_gross": "f_tertiary_enrollment_rates",
        "school_enrollment__tertiary__male__pct_gross": "m_tertiary_enrollment_rates",
    }

    enrolment_wb = tb_wb[select_enrolment_cols]
    enrolment_wb.rename(columns=dictionary_to_rename_and_combine, inplace=True)
    enrolment_wb["mf_secondary_enrollment_rates"] = (
        enrolment_wb["total_net_enrolment_rate__lower_secondary__both_sexes__pct"]
        + enrolment_wb["total_net_enrolment_rate__upper_secondary__both_sexes__pct"]
    ) / 2

    enrolment_wb["m_secondary_enrollment_rates"] = (
        enrolment_wb["total_net_enrolment_rate__lower_secondary__male__pct"]
        + enrolment_wb["total_net_enrolment_rate__upper_secondary__male__pct"]
    ) / 2

    enrolment_wb["f_secondary_enrollment_rates"] = (
        enrolment_wb["total_net_enrolment_rate__lower_secondary__female__pct"]
        + enrolment_wb["total_net_enrolment_rate__upper_secondary__female__pct"]
    ) / 2
    enrolment_wb.drop(
        [
            "total_net_enrolment_rate__lower_secondary__both_sexes__pct",
            "total_net_enrolment_rate__upper_secondary__both_sexes__pct",
            "total_net_enrolment_rate__lower_secondary__female__pct",
            "total_net_enrolment_rate__upper_secondary__female__pct",
            "total_net_enrolment_rate__lower_secondary__male__pct",
            "total_net_enrolment_rate__upper_secondary__male__pct",
        ],
        axis=1,
        inplace=True,
    )
    df_above_2010 = enrolment_wb[(enrolment_wb.index.get_level_values("year") > 2010)]
    df_above_2010.reset_index(inplace=True)

    # Load regions dataset.
    ds_regions: Dataset = paths.load_dependency("regions")

    # Load income groups dataset.
    ds_income_groups: Dataset = paths.load_dependency("income_groups")
    # Read table from meadow dataset.
    tb = ds_meadow["education_lee_lee"]
    tb.reset_index(inplace=True)

    #
    # Process data.
    #
    tb: Table = geo.harmonize_countries(df=tb, countries_file=paths.country_mapping_path)
    tb["age_group"] = tb["age_group"].replace(
        {
            "15.0-64.0": "Youth and Adults (15-64 years)",
            "15.0-24.0": "Youth (15-24 years)",
            "25.0-64.0": "Adults (25-64 years)",
            "not specified": "Age not specified",
        }
    )
    # Clean and pivot enrollment data by sex
    df_enrollment = prepare_enrollment_data(tb)
    df_enrollment = add_data_for_regions(
        tb=df_enrollment, regions=REGIONS, ds_regions=ds_regions, ds_income_groups=ds_income_groups
    )
    # Clean and pivot attainment data by sex and age
    df_attainment = prepare_attainment_data(tb)
    columns_to_check = df_attainment.columns.drop(["country", "year"])
    df_attainment = df_attainment.dropna(subset=columns_to_check, how="all")
    df_attainment.reset_index(drop=True, inplace=True)

    df_attainment = add_data_for_regions(
        tb=df_attainment, regions=REGIONS, ds_regions=ds_regions, ds_income_groups=ds_income_groups
    )
    merged_df = pd.merge(df_enrollment, df_attainment, on=["year", "country"], how="outer")

    # Drop historic population values
    columns_to_drop = [column for column in merged_df.columns if "__thousands" in column]
    merged_df = merged_df.drop(columns=columns_to_drop)
    merged_df.columns = [underscore(col) for col in merged_df.columns]

    df_above_2010 = add_data_for_regions(
        tb=df_above_2010, regions=REGIONS, ds_regions=ds_regions, ds_income_groups=ds_income_groups
    )
    df_merged_enrollment = pd.concat(
        [merged_df[["country", "year"] + list(dictionary_to_rename_and_combine.values())], df_above_2010]
    )
    suffix = "_combined_wb"
    df_merged_enrollment.set_index(["country", "year"], inplace=True)

    wb_combined_columns = df_merged_enrollment.columns + suffix
    df_merged_enrollment.columns = wb_combined_columns

    merged_df.set_index(["country", "year"], inplace=True)

    df_merged_wb = pd.merge(df_merged_enrollment, merged_df, on=["country", "year"], how="outer")
    df_merged_wb = df_merged_wb.dropna(how="all")

    tb = Table(df_merged_wb, short_name=paths.short_name, underscore=True)

    #
    # Save outputs.
    #
    # Create a new garden dataset with the same metadata as the meadow dataset.
    ds_garden = create_dataset(dest_dir, tables=[tb], default_metadata=ds_meadow.metadata)

    # Save changes in the new garden dataset.
    ds_garden.save()


def melt_and_pivot(
    df: pd.DataFrame, id_vars: List[str], value_vars: List[str], index_vars: List[str], columns_vars: List[str]
) -> pd.DataFrame:
    """
    Melt the dataframe to long format and then pivot it to wide format.

    Parameters:
    df (DataFrame): Original dataframe to process.
    id_vars (List[str]): Identifier variables for melting.
    value_vars (List[str]): Column(s) to unpivot.
    index_vars (List[str]): Column(s) to set as index for pivoting.
    columns_vars (List[str]): Column(s) to pivot on.

    Returns:
    DataFrame: Processed dataframe.
    """
    df_melted = df.melt(id_vars=id_vars, value_vars=value_vars, var_name="measurement", value_name="value")
    df_pivot = df_melted.pivot(index=index_vars, columns=columns_vars, values="value")

    return df_pivot


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flatten hierarchical columns in dataframe.

    Parameters:
    df (DataFrame): Dataframe with multi-level columns.

    Returns:
    DataFrame: Dataframe with flattened columns.
    """
    df.columns = ["_".join(col).strip() for col in df.columns.values]
    df = df.reset_index()

    return df


def prepare_enrollment_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare the dataframe by selecting required columns and drop the rows
    where all values in the specified columns are NaN.

    Parameters:
    df (DataFrame): Original dataframe to process.

    Returns:
    DataFrame: Processed dataframe with enrollment data.
    """
    id_vars_enrollment = ["country", "year", "sex"]
    enrollment_columns = ["primary_enrollment_rates", "secondary_enrollment_rates", "tertiary_enrollment_rates"]
    df_enrollment = df[enrollment_columns + id_vars_enrollment]
    df_enrollment = df_enrollment.dropna(subset=enrollment_columns, how="all")
    df_enrollment.reset_index(drop=True, inplace=True)

    df_pivot_enrollment = melt_and_pivot(
        df_enrollment, id_vars_enrollment, enrollment_columns, ["country", "year"], ["sex", "measurement"]
    )
    df_pivot_enrollment = flatten_columns(df_pivot_enrollment)

    return df_pivot_enrollment


def prepare_attainment_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare the dataframe by selecting required columns.

    Parameters:
    df (DataFrame): Original dataframe to process.

    Returns:
    DataFrame: Processed dataframe with attainment data.
    """
    id_vars_attainment = ["country", "year", "sex", "age_group"]
    attainment_columns = [
        "percentage_of_no_education",
        "percentage_of_primary_education",
        "percentage_of_complete_primary_education_attained",
        "percentage_of_secondary_education",
        "percentage_of_complete_secondary_education_attained",
        "percentage_of_tertiary_education",
        "percentage_of_complete_tertiary_education_attained",
        "average_years_of_education",
        "average_years_of_primary_education",
        "average_years_of_secondary_education",
        "average_years_of_tertiary_education",
        "population__thousands",
    ]

    df_pivot = melt_and_pivot(
        df[id_vars_attainment + attainment_columns],
        id_vars_attainment,
        attainment_columns,
        ["country", "year"],
        ["sex", "age_group", "measurement"],
    )

    df_pivot = flatten_columns(df_pivot)

    cols_to_drop = [col for col in df_pivot.columns if "Age not specified" in col]
    df_pivot = df_pivot.drop(columns=cols_to_drop)

    return df_pivot
