"""Load a meadow dataset and create a garden dataset."""

from typing import cast

from owid.catalog import Dataset, Table

from etl.data_helpers import geo
from etl.helpers import PathFinder, create_dataset

# Get paths and naming conventions for current step.
paths = PathFinder(__file__)

# Define absolute poverty lines used depending on PPP version
povlines_dict = {
    2011: [100, 190, 320, 550, 1000, 2000, 3000, 4000],
    2017: [100, 215, 365, 685, 1000, 2000, 3000, 4000],
}


def process_data(tb: Table) -> Table:
    # rename columns
    tb = tb.rename(columns={"headcount": "headcount_ratio", "poverty_gap": "poverty_gap_index"})

    # Changing the decile(i) variables for decile(i)_share
    for i in range(1, 11):
        tb = tb.rename(columns={f"decile{i}": f"decile{i}_share"})

    # Calculate number in poverty
    tb["headcount"] = tb["headcount_ratio"] * tb["reporting_pop"]
    tb["headcount"] = tb["headcount"].round(0)

    # Calculate shortfall of incomes
    tb["total_shortfall"] = tb["poverty_gap_index"] * tb["poverty_line"] * tb["reporting_pop"]

    # Calculate average shortfall of incomes (averaged across population in poverty)
    tb["avg_shortfall"] = tb["total_shortfall"] / tb["headcount"]

    # Calculate income gap ratio (according to Ravallion's definition)
    tb["income_gap_ratio"] = (tb["total_shortfall"] / tb["headcount"]) / tb["poverty_line"]

    # Same for relative poverty
    for pct in [40, 50, 60]:
        tb[f"headcount_{pct}_median"] = tb[f"headcount_ratio_{pct}_median"] * tb["reporting_pop"]
        tb[f"headcount_{pct}_median"] = tb[f"headcount_{pct}_median"].round(0)
        tb[f"total_shortfall_{pct}_median"] = (
            tb[f"poverty_gap_index_{pct}_median"] * tb["median"] * pct / 100 * tb["reporting_pop"]
        )
        tb[f"avg_shortfall_{pct}_median"] = tb[f"total_shortfall_{pct}_median"] / tb[f"headcount_{pct}_median"]
        tb[f"income_gap_ratio_{pct}_median"] = (tb[f"total_shortfall_{pct}_median"] / tb[f"headcount_{pct}_median"]) / (
            tb["median"] * pct / 100
        )

    # Shares to percentages
    # executing the function over list of vars
    pct_indicators = ["headcount_ratio", "income_gap_ratio", "poverty_gap_index"]
    tb.loc[:, pct_indicators] = tb[pct_indicators] * 100

    # Create a new column for the poverty line in cents and string
    tb["poverty_line_cents"] = (tb["poverty_line"] * 100).astype(int).astype(str)

    # Make the table wide, with poverty_line_cents as columns
    tb = tb.pivot(
        index=[
            "ppp_version",
            "country",
            "year",
            "reporting_level",
            "welfare_type",
            "survey_comparability",
            "comparable_spell",
            "reporting_pop",
            "mean",
            "median",
            "mld",
            "gini",
            "polarization",
            "decile1_share",
            "decile2_share",
            "decile3_share",
            "decile4_share",
            "decile5_share",
            "decile6_share",
            "decile7_share",
            "decile8_share",
            "decile9_share",
            "decile10_share",
            "decile1_thr",
            "decile2_thr",
            "decile3_thr",
            "decile4_thr",
            "decile5_thr",
            "decile6_thr",
            "decile7_thr",
            "decile8_thr",
            "decile9_thr",
            "is_interpolated",
            "distribution_type",
            "estimation_type",
            "headcount_40_median",
            "headcount_50_median",
            "headcount_60_median",
            "headcount_ratio_40_median",
            "headcount_ratio_50_median",
            "headcount_ratio_60_median",
            "income_gap_ratio_40_median",
            "income_gap_ratio_50_median",
            "income_gap_ratio_60_median",
            "poverty_gap_index_40_median",
            "poverty_gap_index_50_median",
            "poverty_gap_index_60_median",
            "avg_shortfall_40_median",
            "avg_shortfall_50_median",
            "avg_shortfall_60_median",
            "total_shortfall_40_median",
            "total_shortfall_50_median",
            "total_shortfall_60_median",
            "poverty_severity_40_median",
            "poverty_severity_50_median",
            "poverty_severity_60_median",
            "watts_40_median",
            "watts_50_median",
            "watts_60_median",
        ],
        columns="poverty_line_cents",
        values=[
            "headcount",
            "headcount_ratio",
            "income_gap_ratio",
            "poverty_gap_index",
            "avg_shortfall",
            "total_shortfall",
            "poverty_severity",
            "watts",
        ],
    )

    # Flatten column names
    tb.columns = ["_".join(col).strip() for col in tb.columns.values]

    # Reset index
    tb = tb.reset_index()

    return tb


# NOTE: Create stacked variables
def create_stacked_variables(tb: Table, povline_dict: dict, ppp_version: int) -> Table:
    """
    Create stacked variables from the indicators to plot them as stacked area/bar charts
    """

    # Filter table to include only the right ppp_version
    tb = tb[tb["ppp_version"] == ppp_version].reset_index(drop=True)

    # Select poverty lines between 2011 and 2017 and sort in case they are not in order
    povlines = povlines_dict[ppp_version].sort()

    # Above variables

    col_above_n = []
    col_above_pct = []

    for p in povlines:
        varname_n = f"headcount_above_{p}"
        varname_pct = f"headcount_ratio_above_{p}"

        tb[varname_n] = tb["reporting_pop"] - tb[f"headcount_{p}"]
        tb[varname_pct] = tb[varname_n] / tb["reporting_pop"]

        col_above_n.append(varname_n)
        col_above_pct.append(varname_pct)

    tb.loc[:, col_above_pct] = tb[col_above_pct] * 100

    # Stacked variables

    col_stacked_n = []
    col_stacked_pct = []

    for i in range(len(povlines)):
        # if it's the first value only get people below this poverty line (and percentage)
        if i == 0:
            varname_n = f"headcount_stacked_below_{povlines[i]}"
            varname_pct = f"headcount_ratio_stacked_below_{povlines[i]}"
            tb[varname_n] = tb[f"headcount_{povlines[i]}"]
            tb[varname_pct] = tb[varname_n] / tb["reporting_pop"]
            col_stacked_n.append(varname_n)
            col_stacked_pct.append(varname_pct)

        # If it's the last value calculate the people between this value and the previous
        # and also the people over this poverty line (and percentages)
        elif i == len(povlines) - 1:
            varname_n = f"headcount_stacked_below_{povlines[i]}"
            varname_pct = f"headcount_ratio_stacked_below_{povlines[i]}"
            tb[varname_n] = tb[f"headcount_{povlines[i]}"] - tb[f"headcount_{povlines[i-1]}"]
            tb[varname_pct] = tb[varname_n] / tb["reporting_pop"]
            col_stacked_n.append(varname_n)
            col_stacked_pct.append(varname_pct)
            varname_n = f"headcount_stacked_above_{povlines[i]}"
            varname_pct = f"headcount_ratio_stacked_above_{povlines[i]}"
            tb[varname_n] = tb["reporting_pop"] - tb[f"headcount_{povlines[i]}"]
            tb[varname_pct] = tb[varname_n] / tb["reporting_pop"]
            col_stacked_n.append(varname_n)
            col_stacked_pct.append(varname_pct)

        # If it's any value between the first and the last calculate the people between this value and the previous (and percentage)
        else:
            varname_n = f"headcount_stacked_below_{povlines[i]}"
            varname_pct = f"headcount_ratio_stacked_below_{povlines[i]}"
            tb[varname_n] = tb[f"headcount_{povlines[i]}"] - tb[f"headcount_{povlines[i-1]}"]
            tb[varname_pct] = tb[varname_n] / tb["reporting_pop"]
            col_stacked_n.append(varname_n)
            col_stacked_pct.append(varname_pct)

    tb.loc[:, col_stacked_pct] = tb[col_stacked_pct] * 100

    # Calculate stacked variables which "jump" the original order

    tb[f"headcount_stacked_between_{povlines[1]}_{povlines[4]}"] = (
        tb[f"headcount_{povlines[4]}"] - tb[f"headcount_{povlines[1]}"]
    )
    tb[f"headcount_stacked_between_{povlines[4]}_{povlines[6]}"] = (
        tb[f"headcount_{povlines[6]}"] - tb[f"headcount_{povlines[4]}"]
    )

    tb[f"headcount_ratio_stacked_between_{povlines[1]}_{povlines[4]}"] = (
        tb[f"headcount_ratio_{povlines[4]}"] - tb[f"headcount_ratio_{povlines[1]}"]
    )
    tb[f"headcount_ratio_stacked_between_{povlines[4]}_{povlines[6]}"] = (
        tb[f"headcount_ratio_{povlines[6]}"] - tb[f"headcount_ratio_{povlines[4]}"]
    )


def calculate_inequality(tb: Table) -> Table:
    """
    Calculate inequality measures: decile averages and ratios
    """
    # NOTE: I need the thresholds to complete this function

    col_decile_share = []
    col_decile_avg = []
    col_decile_thr = []

    for i in range(1, 11):
        if i != 10:
            varname_thr = f"decile{i}_thr"
            col_decile_thr.append(varname_thr)

        varname_share = f"decile{i}_share"
        varname_avg = f"decile{i}_avg"
        tb[varname_avg] = tb[varname_share] * tb["mean"] / 0.1

        col_decile_share.append(varname_share)
        col_decile_avg.append(varname_avg)

    # Multiplies decile columns by 100
    tb.loc[:, col_decile_share] = tb[col_decile_share] * 100

    # Palma ratio and other average/share ratios
    tb["palma_ratio"] = tb["decile10_share"] / (
        tb["decile1_share"] + tb["decile2_share"] + tb["decile3_share"] + tb["decile4_share"]
    )
    tb["s80_s20_ratio"] = (tb["decile9_share"] + tb["decile10_share"]) / (tb["decile1_share"] + tb["decile2_share"])
    tb["p90_p10_ratio"] = tb["decile9_thr"] / tb["decile1_thr"]
    tb["p90_p50_ratio"] = tb["decile9_thr"] / tb["decile5_thr"]
    tb["p50_p10_ratio"] = tb["decile5_thr"] / tb["decile1_thr"]


def identify_rural_urban(tb: Table) -> Table:
    """
    Amend the entity to reflect if data refers to urban or rural only
    """

    tb.loc[(tb["reporting_level"].isin(["urban", "rural"])), "country"] = (
        tb.loc[(tb["reporting_level"].isin(["urban", "rural"])), "country"]
        + " ("
        + tb.loc[(tb["reporting_level"].isin(["urban", "rural"])), "reporting_level"]
        + ")"
    )

    return tb


def sanity_checks(tb: Table, povlines_dict: dict, ppp_version: int) -> Table:
    """
    Sanity checks for the table
    """

    # stacked values not adding up to 100%
    print(f"{len(tb)} rows before stacked values check")
    tb["sum_pct"] = tb[col_stacked_pct].sum(axis=1)
    tb = tb[~((tb["sum_pct"] >= 100.1) | (tb["sum_pct"] <= 99.9))].reset_index(drop=True)
    print(f"{len(tb)} rows after stacked values check")

    # missing poverty values (headcount, poverty gap, total shortfall)
    print(f"{len(tb)} rows before missing values check")
    cols_to_check = (
        col_headcount + col_headcount_ratio + col_povertygap + col_tot_shortfall + col_stacked_n + col_stacked_pct
    )
    tb = tb[~tb[cols_to_check].isna().any(1)].reset_index(drop=True)
    print(f"{len(tb)} rows after missing values check")

    # headcount monotonicity check
    print(f"{len(tb)} rows before headcount monotonicity check")
    m_check_vars = []
    for i in range(len(col_headcount)):
        if i > 0:
            check_varname = f"m_check_{i}"
            tb[check_varname] = tb[f"{col_headcount[i]}"] >= tb[f"{col_headcount[i-1]}"]
            m_check_vars.append(check_varname)
    tb["check_total"] = tb[m_check_vars].all(1)
    tb = tb[tb["check_total"] == True].reset_index(drop=True)
    print(f"{len(tb)} rows after headcount monotonicity check")

    return tb


def inc_or_cons_data(tb: Table) -> Table:
    """
    Separate income and consumption data
    """

    # Separate out consumption-only, income-only. Also, create a table with both income and consumption
    tb_inc = tb[tb["welfare_type"] == "income"].reset_index(drop=True)
    tb_cons = tb[tb["welfare_type"] == "consumption"].reset_index(drop=True)
    tb_inc_or_cons = tb.copy()

    # If both inc and cons are available in a given year, drop inc

    # Flag duplicates – indicating multiple welfare_types
    # Sort values to ensure the welfare_type consumption is marked as False when there are multiple welfare types
    tb_inc_or_cons = tb_inc_or_cons.sort_values(
        by=["ppp_version", "country", "year", "reporting_level", "welfare_type"], ignore_index=True
    )
    tb_inc_or_cons["duplicate_flag"] = tb_inc_or_cons.duplicated(
        subset=["ppp_version", "country", "year", "reporting_level"]
    )

    # Drop income where income and consumption are available
    tb_inc_or_cons = tb_inc_or_cons[
        (tb_inc_or_cons["duplicate_flag"] == False) | (tb_inc_or_cons["welfare_type"] == "consumption")
    ]
    tb_inc_or_cons.drop(columns=["duplicate_flag"], inplace=True)

    # print(f'After dropping duplicates there were {len(tb_inc_or_cons)} rows.')

    return tb_inc, tb_cons, tb_inc_or_cons


def run(dest_dir: str) -> None:
    #
    # Load inputs.
    #
    # Load meadow dataset.
    ds_meadow = cast(Dataset, paths.load_dependency("world_bank_pip"))

    # Read table from meadow dataset.
    tb = ds_meadow["world_bank_pip"].reset_index()

    #

    # Process data: Make table wide and change column names
    tb = process_data(tb)

    # Calculate inequality measures
    tb = calculate_inequality(tb)

    #
    # NOTE: Separate income and consumption data.

    tb: Table = geo.harmonize_countries(df=tb, countries_file=paths.country_mapping_path)

    # Amend the entity to reflect if data refers to urban or rural only
    tb = identify_rural_urban(tb)

    tb_2011 = create_stacked_variables(tb, povlines_dict, ppp_version=2011)
    tb_2017 = create_stacked_variables(tb, povlines_dict, ppp_version=2017)

    # Sanity checks
    tb_2011 = sanity_checks(tb_2011, povlines_dict, ppp_version=2011)
    tb_2017 = sanity_checks(tb_2017, povlines_dict, ppp_version=2017)

    # Separate out consumption-only, income-only. Also, create a table with both income and consumption
    tb_inc_2011, tb_cons_2011, tb_inc_or_cons_2011 = inc_or_cons_data(tb_2011)
    tb_inc_2017, tb_cons_2017, tb_inc_or_cons_2017 = inc_or_cons_data(tb_2017)

    # Define tables to upload
    tables = [tb_inc_2011, tb_cons_2011, tb_inc_or_cons_2011, tb_inc_2017, tb_cons_2017, tb_inc_or_cons_2017]

    # Set index and sort
    for tb in tables:
        tb = tb.set_index(["country", "year"], verify_integrity=True).sort_index()

    #
    # Save outputs.
    #
    # Create a new garden dataset with the same metadata as the meadow dataset.
    ds_garden = create_dataset(dest_dir, tables=[tables], default_metadata=ds_meadow.metadata)

    # Save changes in the new garden dataset.
    ds_garden.save()
