"""
This file includes functions to get variables metadata in the `moatsos_historical_poverty` garden step
If new poverty lines or indicators are included, they need to be addressed here
"""

from owid.catalog import Table, VariableMeta

# These is text common to all variables

cbd_description = """
- The ‘cost of basic needs’ approach was recommended by the World Bank Commission on Global Poverty, headed by Tony Atkinson, as a complementary method in measuring poverty.

- Moatsos describes the methodology as follows: “In this approach, poverty lines are calculated for every year and country separately, rather than using a single global line. The second step is to gather the necessary data to operationalize this approach alongside imputation methods in cases where not all the necessary data are available. The third step is to devise a method for aggregating countries’ poverty estimates on a global scale to account for countries that lack some of the relevant data.”
"""

dod_description = """
Data after 1981 relates to household income or consumption surveys collated by the World Bank; before 1981 it is based on historical reconstructions of GDP per capita and inequality data.
"""

ppp_description = "The data is measured in international-$ at 2011 prices – this adjusts for inflation and for differences in the cost of living between countries."

# These are parameters specifically defined for each type of variable
var_dict = {
    "headcount": {
        "title": "Number in poverty",
        "description": "Number of people {povline}",
        "unit": "",
        "short_unit": "",
        "numDecimalPlaces": 0,
    },
    "headcount_ratio": {
        "title": "Share of population in poverty",
        "description": "Share of the population {povline}",
        "unit": "%",
        "short_unit": "%",
        "numDecimalPlaces": 1,
    },
}

# Details for each absolute poverty line
povline_dict = {
    190: {"title": "$1.90 a day", "description": "living below $1.90 a day"},
    500: {"title": "$5 a day", "description": "living below $5 a day"},
    1000: {"title": "$10 a day", "description": "living below $10 a day"},
    3000: {"title": "$30 a day", "description": "living below $30 a day"},
}

cbn_dict = {
    "cbn": {
        "title": "Cost of Basic Needs",
        "description": "unable to meet basic needs (including minimal nutrition and adequately heated shelter) according to prices of locally-available goods and services at the time.",
    },
}


# This function creates the metadata for each variable in the dataset, from the dictionaries defined above
def add_metadata_vars(tb_garden: Table):
    # Get a list of all the variables available
    cols = list(tb_garden.columns)

    for var in var_dict:
        for povline in povline_dict:
            # For variables that "dollar a day" poverty lines
            col_name = f"{var}_{povline}"

            if col_name in cols:
                # Create metadata for these variables
                tb_garden[col_name].metadata = var_metadata_absolute(var, povline)

                tb_garden[col_name].metadata.description = tb_garden[col_name].metadata.description_short.replace(
                    "{povline}", str(povline_dict[povline]["description"])
                )

        for cbn in cbn_dict:
            # For variables that use the CBN method
            col_name = f"{var}_{cbn}"

            if col_name in cols:
                # Create metadata for these variables
                tb_garden[col_name].metadata = var_metadata_cbn(var, cbn)

                tb_garden[col_name].metadata.description = tb_garden[col_name].metadata.description_short.replace(
                    "{povline}", cbn_dict[cbn]["description"]
                )

            for rel in rel_dict:
                # For variables that use income variable, equivalence scale and relative poverty lines
                col_name = f"{var}_{rel}_median_{wel}_{e}"

                if col_name in cols:
                    # Create metadata for these variables
                    tb_garden[col_name].metadata = var_metadata_income_equivalence_scale_relative(var, wel, e, rel)

                    # Replace values in description according to `rel`
                    tb_garden[col_name].metadata.description = tb_garden[col_name].metadata.description.replace(
                        "{povline}", rel_dict[rel]
                    )

            for abs in abs_dict:
                # For variables that use income variable, equivalence scale and absolute poverty lines
                col_name = f"{var}_{wel}_{e}_{abs}"

                if col_name in cols:
                    # Create metadata for these variables
                    tb_garden[col_name].metadata = var_metadata_income_equivalence_scale_absolute(var, wel, e, abs)

                    # Replace values in description according to `abs`
                    tb_garden[col_name].metadata.description = tb_garden[col_name].metadata.description.replace(
                        "{povline}", abs_dict[abs]
                    )

            for pct in pct_dict:
                # For variables that use income variable, equivalence scale and percentiles (deciles)
                col_name = f"{var}_p{pct}_{wel}_{e}"

                if col_name in cols:
                    # Create metadata for these variables
                    tb_garden[col_name].metadata = var_metadata_income_equivalence_scale_percentiles(var, wel, e, pct)

                    # Replace values in description according to `pct`, depending on `var`
                    if var == "thr":
                        tb_garden[col_name].metadata.description = tb_garden[col_name].metadata.description.replace(
                            "{str(pct)}", str(pct)
                        )

                    else:
                        tb_garden[col_name].metadata.description = tb_garden[col_name].metadata.description.replace(
                            "{pct_dict[pct]['decile10']}", pct_dict[pct]["decile10"].lower()
                        )

                    # Replace income/wealth words according to `wel`
                    tb_garden[col_name].metadata.description = tb_garden[col_name].metadata.description.replace(
                        "{inc_cons_dict[wel]['verb']}", str(inc_cons_dict[wel]["verb"])
                    )
                    tb_garden[col_name].metadata.description = tb_garden[col_name].metadata.description.replace(
                        "{inc_cons_dict[wel]['type']}", str(inc_cons_dict[wel]["type"])
                    )

    return tb_garden


# Metadata functions to show a clearer main code
def var_metadata_absolute(var, povline) -> VariableMeta:
    meta = VariableMeta(
        title=f"{povline_dict[povline]['title']} - {var_dict[var]['title']}",
        description_short=f"""{var_dict[var]['description']}""",
        description_key=f"""
        - {ppp_description}
        - {dod_description}""",
        unit=var_dict[var]["unit"],
        short_unit=var_dict[var]["short_unit"],
    )
    meta.display = {
        "name": meta.title,
        "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
    }

    return meta


def var_metadata_cbn(var, cbn) -> VariableMeta:
    meta = VariableMeta(
        title=f"{cbn_dict[cbn]['title']} - {var_dict[var]['title']}",
        description_short=f"""{var_dict[var]['description']}""",
        description_key=f"""{cbd_description}""",
        unit=var_dict[var]["unit"],
        short_unit=var_dict[var]["short_unit"],
    )
    meta.display = {
        "name": meta.title,
        "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
    }

    return meta


def var_metadata_income_equivalence_scale_relative(var, wel, e, rel) -> VariableMeta:
    meta = VariableMeta(
        title=f"{rel_dict[rel]} - {var_dict[var]['title']} ({inc_cons_dict[wel]['name']}, {equivalence_scales_dict[e]['name']})",
        description=f"""{var_dict[var]['description']}

        {inc_cons_dict[wel]['description']}

        {equivalence_scales_dict[e]['description']}

        {notes_title}

        {processing_description}

        {processing_poverty}""",
        unit=var_dict[var]["unit"],
        short_unit=var_dict[var]["short_unit"],
    )
    meta.display = {
        "name": meta.title,
        "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
    }
    return meta


def var_metadata_income_equivalence_scale_absolute(var, wel, e, abs) -> VariableMeta:
    meta = VariableMeta(
        title=f"{abs_dict[abs]} - {var_dict[var]['title']} ({inc_cons_dict[wel]['name']}, {equivalence_scales_dict[e]['name']})",
        description=f"""{var_dict[var]['description']}

        {inc_cons_dict[wel]['description']}

        {equivalence_scales_dict[e]['description']}

        {ppp_description}

        {notes_title}

        {processing_description}

        {processing_poverty}""",
        unit=var_dict[var]["unit"],
        short_unit=var_dict[var]["short_unit"],
    )
    meta.display = {
        "name": meta.title,
        "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
    }
    return meta


def var_metadata_income_equivalence_scale_percentiles(var, wel, e, pct) -> VariableMeta:
    if var == "thr":
        meta = VariableMeta(
            title=f"{pct_dict[pct]['decile9']} - {var_dict[var]['title']} ({inc_cons_dict[wel]['name']}, {equivalence_scales_dict[e]['name']})",
            description=f"""{var_dict[var]['description']}

            {inc_cons_dict[wel]['description']}

            {equivalence_scales_dict[e]['description']}

            {ppp_description}

            {notes_title}

            {processing_description}

            {processing_distribution}""",
            unit=var_dict[var]["unit"],
            short_unit=var_dict[var]["short_unit"],
        )
        meta.display = {
            "name": meta.title,
            "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
        }

    elif var == "avg":
        meta = VariableMeta(
            title=f"{pct_dict[pct]['decile10']} - {var_dict[var]['title']} ({inc_cons_dict[wel]['name']}, {equivalence_scales_dict[e]['name']})",
            description=f"""{var_dict[var]['description']}

            {inc_cons_dict[wel]['description']}

            {equivalence_scales_dict[e]['description']}

            {ppp_description}

            {notes_title}

            {processing_description}

            {processing_distribution}""",
            unit=var_dict[var]["unit"],
            short_unit=var_dict[var]["short_unit"],
        )
        meta.display = {
            "name": meta.title,
            "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
        }
    # Shares do not show PPP description
    else:
        meta = VariableMeta(
            title=f"{pct_dict[pct]['decile10']} - {var_dict[var]['title']} ({inc_cons_dict[wel]['name']}, {equivalence_scales_dict[e]['name']})",
            description=f"""{var_dict[var]['description']}

            {inc_cons_dict[wel]['description']}

            {equivalence_scales_dict[e]['description']}

            {notes_title}

            {processing_description}

            {processing_distribution}""",
            unit=var_dict[var]["unit"],
            short_unit=var_dict[var]["short_unit"],
        )
        meta.display = {
            "name": meta.title,
            "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
        }
    return meta


##############################################################################################################
# This is the code for the distribution variables
##############################################################################################################

var_dict_distribution = {
    # "avg": {
    #     "title": "Average",
    #     "description": "The mean income per year within each percentile.",
    #     "unit": "international-$ in 2017 prices",
    #     "short_unit": "$",
    #     "numDecimalPlaces": 0,
    # },
    "share": {
        "title": "Share",
        "description": "The share of income received by each percentile.",
        "unit": "%",
        "short_unit": "%",
        "numDecimalPlaces": 1,
    },
    "thr": {
        "title": "Threshold",
        "description": "The level of income per year below which 1%, 2%, 3%, ... , 99% of the population falls.",
        "unit": "international-$ in 2017 prices",
        "short_unit": "$",
        "numDecimalPlaces": 0,
    },
}

# Define welfare variables

welfare_definitions = """Data refers to three types of welfare measures:

- `welfare = "mi"` is market income, ‘pre-tax’ income — measured before taxes have been paid and most government benefits have been received.

- `welfare = "dhi"` is disposable household income, ‘post-tax’ income — measured after taxes have been paid and most government benefits have been received.

- `welfare = "dhci"` is disposable household cash income ‘post-tax’ income — measured after taxes have been paid and most government benefits have been received and excluding fringe benefits, home production, in-kind benefits and transfers.

"""

equivalence_scales_definitions = """Data is processed in two different ways:

- `equivalence_scale = "eq"` is equivalized income – adjusted to account for the fact that people in the same household can share costs like rent and heating.

- `equivalence_scale = "pc"` is per capita income, which means that each person (including children) is attributed an equal share of the total income received by all members of their household.

"""


def add_metadata_vars_distribution(tb_garden: Table) -> Table:
    # Get a list of all the variables available
    cols = list(tb_garden.columns)

    for var in var_dict_distribution:
        # All the variables follow whis structure
        col_name = f"{var}"

        if col_name in cols:
            # Create metadata for these variables
            tb_garden[col_name].metadata = var_metadata_distribution(var)

    return tb_garden


def var_metadata_distribution(var: str) -> VariableMeta:
    """
    This function assigns each of the metadata fields for the distribution variables
    """
    # Shares do not include PPP description
    if var == "share":
        meta = VariableMeta(
            title=f"Income {var_dict_distribution[var]['title'].lower()}",
            description=f"""{var_dict_distribution[var]['description']}

            {welfare_definitions}

            {equivalence_scales_definitions}

            {notes_title}

            {processing_description}

            {processing_distribution}""",
            unit=var_dict_distribution[var]["unit"],
            short_unit=var_dict_distribution[var]["short_unit"],
        )
        meta.display = {
            "name": meta.title,
            "numDecimalPlaces": var_dict_distribution[var]["numDecimalPlaces"],
        }

    # For monetary variables I include the PPP description
    else:
        meta = VariableMeta(
            title=f"{var_dict_distribution[var]['title']} income",
            description=f"""{var_dict_distribution[var]['description']}

            {welfare_definitions}

            {equivalence_scales_definitions}

            {ppp_description}

            {notes_title}

            {processing_description}

            {processing_distribution}""",
            unit=var_dict_distribution[var]["unit"],
            short_unit=var_dict_distribution[var]["short_unit"],
        )
        meta.display = {
            "name": meta.title,
            "numDecimalPlaces": var_dict_distribution[var]["numDecimalPlaces"],
        }

    return meta
