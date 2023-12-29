"""
This file includes functions to get variables metadata in the `moatsos_historical_poverty` garden step
If new poverty lines or indicators are included, they need to be addressed here
"""

from owid.catalog import Table, VariableMeta

# These is text common to all variables

cbd_description_1 = """
The ‘cost of basic needs’ approach was recommended by the World Bank Commission on Global Poverty, headed by Tony Atkinson, as a complementary method in measuring poverty.
"""

cbd_description_2 = """
Moatsos describes the methodology as follows: “In this approach, poverty lines are calculated for every year and country separately, rather than using a single global line. The second step is to gather the necessary data to operationalize this approach alongside imputation methods in cases where not all the necessary data are available. The third step is to devise a method for aggregating countries’ poverty estimates on a global scale to account for countries that lack some of the relevant data.”
"""

dod_description = """
Data after 1981 relates to household income or consumption surveys collated by the World Bank; before 1981 it is based on historical reconstructions of GDP per capita and inequality data.
"""

ppp_description = "The data is measured in international-$ at 2011 prices – this adjusts for inflation and for differences in the cost of living between countries."

processing_description = """
From the share and number unable to meet basic needs available in the dataset, we can estimate the number below different "dollar a day" poverty lines. Additionally, we estimate the share and number above these poverty lines, as well between them. We also estimate the share and number of people able to meet basic needs.
"""

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
    190: {"title": "$1.90 a day", "title_between": "$1.90", "description": "living below $1.90 a day"},
    500: {"title": "$5 a day", "title_between": "$5", "description": "living below $5 a day"},
    1000: {"title": "$10 a day", "title_between": "$10", "description": "living below $10 a day"},
    3000: {"title": "$30 a day", "title_between": "$30", "description": "living below $30 a day"},
}

cbn_dict = {
    "cbn": {
        "title": "Cost of Basic Needs",
        "description": "unable to meet basic needs (including minimal nutrition and adequately heated shelter) according to prices of locally-available goods and services at the time.",
    },
}

# Create a list from povline_dict
povline_list = list(povline_dict.keys())


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

                tb_garden[col_name].metadata.description_short = tb_garden[col_name].metadata.description_short.replace(
                    "{povline}", str(povline_dict[povline]["description"])
                )

            # For variables above poverty lines
            col_name = f"{var}_above_{povline}"

            if col_name in cols:
                # Create metadata for these variables
                tb_garden[col_name].metadata = var_metadata_absolute(var, povline)

                tb_garden[col_name].metadata.description_short = tb_garden[col_name].metadata.description_short.replace(
                    "{povline}", str(povline_dict[povline]["description"])
                )

                tb_garden[col_name].metadata.description_short = tb_garden[col_name].metadata.description_short.replace(
                    "below", "above"
                )
                tb_garden[col_name].metadata.title = tb_garden[col_name].metadata.title.replace(
                    "in poverty", "not in poverty"
                )
                tb_garden[col_name].metadata.display["name"] = tb_garden[col_name].metadata.title

        for cbn in cbn_dict:
            # For variables that use the CBN method
            col_name = f"{var}_{cbn}"

            if col_name in cols:
                # Create metadata for these variables
                tb_garden[col_name].metadata = var_metadata_cbn(var, cbn)

                tb_garden[col_name].metadata.description_short = tb_garden[col_name].metadata.description_short.replace(
                    "{povline}", cbn_dict[cbn]["description"]
                )

            # For variables above CBN
            col_name = f"{var}_above_{cbn}"

            if col_name in cols:
                # Create metadata for these variables
                tb_garden[col_name].metadata = var_metadata_cbn(var, cbn)

                tb_garden[col_name].metadata.description_short = tb_garden[col_name].metadata.description_short.replace(
                    "{povline}", cbn_dict[cbn]["description"]
                )

                tb_garden[col_name].metadata.description_short = tb_garden[col_name].metadata.description_short.replace(
                    "below", "above"
                )
                tb_garden[col_name].metadata.title = tb_garden[col_name].metadata.title.replace(
                    "in poverty", "not in poverty"
                )
                tb_garden[col_name].metadata.display["name"] = tb_garden[col_name].metadata.title

        for i in range(len(povline_list)):
            if i != 0:
                # For variables between poverty lines
                col_name = f"{var}_between_{povline_list[i-1]}_{povline_list[i]}"

                if col_name in cols:
                    # Create metadata for these variables
                    tb_garden[col_name].metadata = var_metadata_between(var, povline_list[i - 1], povline_list[i])

                    tb_garden[col_name].metadata.description_short = tb_garden[
                        col_name
                    ].metadata.description_short.replace(
                        "{povline}",
                        f"living between {povline_dict[povline_list[i-1]]['title_between']} and {povline_dict[povline_list[i]]['title_between']} a day",
                    )

    return tb_garden


# Metadata functions to show a clearer main code
def var_metadata_absolute(var, povline) -> VariableMeta:
    meta = VariableMeta(
        title=f"{povline_dict[povline]['title']} - {var_dict[var]['title']}",
        description_short=var_dict[var]["description"],
        description_key=[ppp_description, dod_description],
        description_processing=processing_description,
        unit=var_dict[var]["unit"],
        short_unit=var_dict[var]["short_unit"],
    )
    meta.display = {
        "name": meta.title,
        "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
        "entityAnnotationsMap": "Western offshoots (Moatsos): United States, Canada, Australia and New Zealand",
    }

    return meta


def var_metadata_between(var, povline1, povline2) -> VariableMeta:
    meta = VariableMeta(
        title=f"{povline_dict[povline1]['title_between']}-{povline_dict[povline2]['title_between']} - {var_dict[var]['title']}",
        description_short=var_dict[var]["description"],
        description_key=[ppp_description, dod_description],
        description_processing=processing_description,
        unit=var_dict[var]["unit"],
        short_unit=var_dict[var]["short_unit"],
    )
    meta.display = {
        "name": meta.title,
        "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
        "entityAnnotationsMap": "Western offshoots (Moatsos): United States, Canada, Australia and New Zealand",
    }

    return meta


def var_metadata_cbn(var, cbn) -> VariableMeta:
    meta = VariableMeta(
        title=f"{cbn_dict[cbn]['title']} - {var_dict[var]['title']}",
        description_short=var_dict[var]["description"],
        description_key=[cbd_description_1, cbd_description_2],
        description_processing=processing_description,
        unit=var_dict[var]["unit"],
        short_unit=var_dict[var]["short_unit"],
    )
    meta.display = {
        "name": meta.title,
        "numDecimalPlaces": var_dict[var]["numDecimalPlaces"],
        "entityAnnotationsMap": "Western offshoots (Moatsos): United States, Canada, Australia and New Zealand",
    }

    return meta
