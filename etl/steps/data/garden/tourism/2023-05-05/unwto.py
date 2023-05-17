"""Load a meadow dataset and create a garden dataset."""

import pandas as pd
from owid.catalog import Dataset, Table
from structlog import get_logger
import numpy as np
from etl.data_helpers import geo
from etl.helpers import PathFinder, create_dataset

log = get_logger()

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)

def shorten_name(name):
    # remove underscores and convert to title case
    name = name.replace('_', ' ').title()

    # extract first letter of each word
    words = name.split()
    initials = '_'.join([word[:2].lower() for word in words])

    return initials

def per_1000(df, column):
    return df[column] / (df['population']/1000)


def convert_columns_to_float32(df):
    for col in df.columns:
        if df[col].dtype != 'float32':
            df[col] = df[col].astype(str).replace(['', '<NA>'], np.nan).astype('float32')
    return df

def shorten_column_names(df):
    newnames = [shorten_name(name) for name in df.columns]
    df.columns = newnames
    return df

def calculate_sum_by_year(df):
    regional_columns = ['in_to_re_af', 'in_to_re_am', 'in_to_re_ea_as_an_th_pa', 'in_to_re_eu', 'in_to_re_mi_ea', 'in_to_re_ot_no_cl', 'in_to_re_so_as']
    df_sum = df[regional_columns].reset_index().groupby('year').sum(numeric_only=True)
    df_sum.columns = ['Africa (UNWTO)', 'Americas (UNWTO)', 'East Asia and the Pacific (UNWTO)', 'Europe (UNWTO)', 'Middle East (UNWTO)', 'Not classified (UNWTO)', 'South Asia (UNWTO)']
    return df_sum

def calculate_sum_by_year_Bonaire_Sint_Eustatius_Saba(merged_df):
    numeric_cols = merged_df.select_dtypes(include=np.number).columns
    sum_by_year = {}
    for col in numeric_cols[1:]:
        sum_by_year[col] = merged_df[merged_df['country'].isin(['Saba', 'Sint Eustatius', 'Bonaire'])].groupby(['year'])[col].apply(lambda x: x.sum(skipna=False))
    sum_by_year = pd.DataFrame(sum_by_year)
    sum_by_year['country'] = 'Bonaire Sint Eustatius and Saba'
    sum_by_year = sum_by_year.reset_index()
    return sum_by_year

def concatenate_dataframes(df, df_sum):
    df_melted = df_sum.melt(id_vars=['year'], var_name='country', value_name='inb_tour_region')
    merged_df = pd.concat([df.reset_index(), df_melted], axis=0)
    return merged_df



def run(dest_dir: str) -> None:
    log.info("unwto.start")
    # Load inputs.
    #
    # Load meadow dataset.
    ds_meadow: Dataset = paths.load_dependency("unwto")

    # Read table from meadow dataset.
    tb_meadow = ds_meadow["unwto"]

    # Create a dataframe with data from the table.
    df = pd.DataFrame(tb_meadow)

    #
    # Process data.
    #
    log.info("unwto.harmonize_countries")
    df = geo.harmonize_countries(
        df=df, countries_file=paths.country_mapping_path, excluded_countries_file=paths.excluded_countries_path
    )

    # Set multi-level index
    df.set_index(['country', 'year'], inplace=True)
    assert len(df.index.levels) == 2 and df.index.is_unique, "Index is not well constructed"

    df = convert_columns_to_float32(df)
    df = shorten_column_names(df)
    df_sum = calculate_sum_by_year(df)
    df_sum.reset_index(inplace = True)
    merged_df = concatenate_dataframes(df, df_sum)
    sum_bon_sint_saba = calculate_sum_by_year_Bonaire_Sint_Eustatius_Saba(merged_df)
    merged_df_drop_ = merged_df.drop(merged_df[merged_df['country'].isin(['Saba', 'Sint Eustatius', 'Bonaire'])].index)
    merged_df_concat = pd.concat([merged_df_drop_, sum_bon_sint_saba], axis=0)


    # Set and reset index
    merged_df_concat = merged_df_concat.set_index(['country', 'year'])
    assert len(merged_df_concat.index.levels) == 2 and merged_df_concat.index.is_unique, "Index is not well constructed"
    merged_df_concat = merged_df_concat.reset_index()

    # Aggregate data by region
    # Africa, Oceania, and income level categories
    regions_ = ["North America",
        "South America",
        "Europe",
        "Africa",
        "Asia",
        "Oceania",
        "European Union (27)"]

    # Add region aggregates to the DataFrame
    #for region in regions_:
    #    merged_df_concat = geo.add_region_aggregates(df=merged_df_concat, country_col='country', year_col='year', region=region)

    # Add population data to the DataFrame
    merged_df_concat_transf = geo.add_population_to_dataframe(
        merged_df_concat, country_col="country", year_col="year", population_col="population"
    )

    # Set and validate the index
    merged_df_concat_transf.set_index(['country', 'year'], inplace=True)
    assert len(merged_df_concat_transf.index.levels) == 2 and merged_df_concat_transf.index.is_unique, "Index is not well constructed"

    # Store the original column names
    original_columns = merged_df_concat_transf.columns.tolist()

    # Drop columns with all NaN values
    merged_df_concat_transf = merged_df_concat_transf.dropna(axis=1, how='all')

    # Store the updated column names
    updated_columns = merged_df_concat_transf.columns.tolist()

    # Print the names of dropped columns
    dropped_columns = [col for col in original_columns if col not in updated_columns]
    print("Dropped columns:", dropped_columns)
    print("Number of remaining columns:", len(merged_df_concat_transf.columns))


    # Convert selected columns to per 1000 individuals
    cols_unit_not_thousands = ['to_in_av_ca_be_pl_pe_10_in', 'to_in_av_le_of_st', 'to_in_nu_of_be_pl', 'to_in_nu_of_es', 'to_in_nu_of_ro', 'to_in_oc_ra_be_pl', 'to_in_oc_ra_ro', 'in_to_ex_pa_tr', 'in_to_ex_tr', 'ou_to_ex_pa_tr', 'ou_to_ex_tr', 'population']

    for col in merged_df_concat_transf.columns:
        if col not in cols_unit_not_thousands:
            merged_df_concat_transf[col] = (merged_df_concat_transf[col] * 1000)


    # Perform calculations on specific columns to transform their values per 1000 individuals
    columns_to_transform = ['ou_to_de_to_de', 'ou_to_de_ov_vi_to', 'ou_to_de_sa_da_vi_ex', 'do_to_tr_to_tr', 'do_to_tr_ov_vi_to', 'do_to_tr_sa_da_vi_ex', 'in_to_ar_to_ar', 'in_to_ar_ov_vi_to', 'in_to_ar_sa_da_vi_ex', 'em_ac_se_fo_vi_ho_an_si_es', 'em_fo_an_be_se_ac', 'em_ot_ac_se', 'em_ot_to_in', 'em_pa_tr', 'em_to', 'em_tr_ag_an_ot_re_se_ac']

    for col in columns_to_transform:
        merged_df_concat_transf[f'{col}_per_1000'] = per_1000(merged_df_concat_transf, col)

    # Calculate the 'bus_pers' column
    merged_df_concat_transf['bus_pers'] = merged_df_concat_transf['in_to_pu_bu_an_pr'] / merged_df_concat_transf['in_to_pu_pe']

    merged_df_concat_transf.reset_index(inplace = True)

    # Create a new table with the processed data.
    tb_garden = Table(merged_df_concat_transf, short_name = 'unwto')

    # Save outputs.
    #
    # Create a new garden dataset with the same metadata as the meadow dataset.
    ds_garden = create_dataset(dest_dir, tables=[tb_garden], default_metadata=None)

    # Save changes in the new garden dataset.
    ds_garden.save()

    log.info("unwto.end")