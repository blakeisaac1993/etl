/*
LIS COMMANDS FOR OUR WORLD IN DATA
This program calculates poverty and inequality estimates for three types of income and one consumption variable:
- dhi: Disposable household income, which is total income minus taxes and social security contributions
- dhci: Disposable household cash income, which is dhi minus the total value of goods and services (fringe benefits, home production, in-kind benefits and transfers)
- mi: Market income, the sum of factor income (labor plus capital income), private income (private cash transfers and in-kind goods and services, not involving goverment) and private pensions
- hcexp: Total consumption, including that stemming from goods and services that have been purchased by the household, and goods ans services that have not been purchased, but either given to the household from somebody else, or self-produced.

The code produces both equivalized and per capita measures for each of these variables.

HOW TO EXECUTE:
1. You first have to register to use LISSY. See http://www.lisdatacenter.org/data-access/lissy/eligibility/ for more details.
2. Once logged in LISSY (https://webui.lisdatacenter.org/userinterface/), in the "edit job" tab select:
	Project: LIS
	Package: Stata
	Subject: "Anything you want"
3. Copy this entire code to the blank space.
4. Adjust settings as needed. For a full update, you need to execute the 6 combinations generated by changing `menu_option` from 1 to 3 and `equivalized` from 0 to 1.
5. Press the green button in the top left ("submit job to postoffice for execution").
6. The execution can take hours if dataset = "all" is selected. You don't have to check constantly, you will get an email to the address you registered once the process finishes.
7. In the email you will find this code and an output in the form of comma-separated values. You have to copy it from top to bottom.
8. Paste the content into a blank file and save it as a csv file (Notepad-like software should be enough for this). The names of the files and the settings related to them are:
	- lis_keyvars_equivalized.csv (menu_option = 1, equivalized = 1)
	- lis_keyvars_pc.csv (menu_option = 1, equivalized = 0)
	- lis_abs_poverty_equivalized.csv (menu_option = 2, equivalized = 1)
	- lis_abs_poverty_pc.csv (menu_option = 2, equivalized = 0)
	- lis_distribution_equivalized.csv (menu_option = 3, equivalized = 1)
	- lis_distribution_pc.csv (menu_option = 3, equivalized = 0)
	- lis_additional_data.csv (menu_option = 4, any equivalized value)
	
9. Repeat the process for the different settings you want to extract.
10. Once all the files have been created, copy them into the lis snapshot directory in the ETL, run concat_files.py and then update the snapshot, by using these comands one by one:
	python snapshots/lis/2023-01-18/concat.py
	python snapshots/lis/2023-01-18/lis_keyvars.py --path-to-file snapshots/lis/2023-01-18/lis_keyvars.csv
	python snapshots/lis/2023-01-18/lis_abs_poverty.py --path-to-file snapshots/lis/2023-01-18/lis_abs_poverty.csv 
	python snapshots/lis/2023-01-18/lis_distribution.py --path-to-file snapshots/lis/2023-01-18/lis_distribution.csv 
	
	(Change the date for future updates)

*/

*
/* SETTINGS
----------------------------------------------------------------------------------------------------------- 
Select data to extract:
1. Population, mean, median, gini and relative poverty variables
2. Absolute poverty variables
3. Decile thresholds and shares
4. Additional dataset information
*/

global menu_option = 1

*Select if the code extracts equivalized (1) or per capita (0) aggregation
global equivalized = 1

*Select the dataset to extract. "all" for the entire LIS data, "test" for test data, small [from(2015) to(2020) iso2(cl uk za)]
global dataset = "all"

*Select the variables to extract
global inc_cons_vars dhi dhci mi hcexp

*Select if relative poverty lines should be obtained from the DHI median (1) or from each welfare variable (0)
global relative_poverty_dhi = 0

*Select if values should be converted to PPPs (1 = yes, 0 = no) and the PPP version (2017 or 2011)
global ppp_values = 1
global ppp_year = 2017

*Define absolute poverty lines (cents)
global abs_povlines 100 215 365 685 1000 2000 3000 4000

*Set the maximum character limit per line
set linesize 255

*-------------------------------------------------------------------------------------------------------------

program define make_variables
	* Identify observations with missing values and drop them
	gen miss_comp = 0
	quietly replace miss_comp=1 if dhi==. | dhci==. | hifactor==. | hiprivate==. | hi33==. | hcexp==.
	quietly drop if miss_comp==1
	
	*Create market income variable
	gen mi = hifactor + hiprivate + hi33
	
	*Get the grossnet variable from the dataset
	quietly levelsof grossnet, local(uniq_gross) clean
	
	foreach var in $inc_cons_vars {
	
		*Get the maximum value of the distribution
		quietly sum `var'
		local max_`var' = r(max)
		
		*If the welfare variable has values >0, calculate top, bottom-coding and equivalization
		if `max_`var'' > 0 {	
			*Use raw income variable
			gen e`var'_b = `var'
			
			*If PPPs are selected and only for countries with PPP data
			if "$ppp_values" == "1" {
				*Convert variable into int-$ at ppp_year prices
				replace e`var'_b = e`var'_b / lisppp
			}
			
			*Replace negative values for zeros
			replace e`var'_b = 0 if `var'<0
			* Apply top and bottom codes / outlier detection
			gen e`var'_log=log(e`var'_b)
			* keep negatives and 0 in the overall distribution of non-missing income
			replace e`var'_log=0 if e`var'_log==. & e`var'_b!=.
			* detect interquartile range
			cap drop iqr
			cap drop upper_bound
			cap drop lower_bound
			qui sum e`var'_log [w=hwgt],de
			gen iqr=r(p75)-r(p25)
			* detect upper bound for extreme values
			gen upper_bound=r(p75) + (iqr * 3)
			gen lower_bound=r(p25) - (iqr * 3)
			* top code income at upper bound for extreme values
			replace e`var'_b=exp(upper_bound) if e`var'_b>exp(upper_bound)
			* bottom code income at lower bound for extreme values
			replace e`var'_b=exp(lower_bound) if e`var'_b<exp(lower_bound)
			
			* If equivalization is selected, the household income is divided by the LIS equivalence scale (squared root of the number of household members)
			if "$equivalized" == "1" {
				replace e`var'_b = (e`var'_b/(nhhmem^0.5))
			}
			
			*If equivalization is not selected, the household income is divided by the number of household members
			else if "$equivalized" == "0" {
				replace e`var'_b = (e`var'_b/(nhhmem))
			}
		}
		
		else {
		
		gen e`var'_b = .
		
		}
		
		*If gross income is not captured in the survey we don't want `mi'. Values correspond to taxes and contributions not captured (200) or partially captured (300, 310, 320). When this data is fully captured grossnet equals 100, 110 means this data is collected and 120 means this data is imputed
		
		if "`var'" == "mi" & ("`uniq_gross'" == "200" | "`uniq_gross'" == "300" | "`uniq_gross'" == "310" | "`uniq_gross'" == "320" | "`uniq_gross'" == ".") {
			replace e`var'_b = .
		}
		
		*If this option is selected, the relative poverty is estimated considering the median of each welfare variable
		if "$relative_poverty_dhi" == "0" {
		
			quietly sum e`var'_b [w=hwgt*nhhmem], de
			forvalues pct = 40(10)60 {
				global povline_`pct'_`var' = r(p50)*`pct'/100
			}
		}
	}
	
	*If this option is selected, the relative poverty is estimated using the median DHI
	if "$relative_poverty_dhi" == "1" {
		quietly sum edhi_b [w=hwgt*nhhmem], de
		*Why edhi_b and not e`var'_b???
		*LIS methodology always uses (equivalized) disposable household income for the relative poverty line
		forvalues pct = 40(10)60 {
			global povline_`pct' = r(p50)*`pct'/100
		}
	}
	
	*Get total population
	quietly sum nhhmem [w=hpopwgt]
	global pop: di %10.0f r(sum)
end

*Use PPP data
if "$ppp_values" == "1" {
	use $myincl/ppp_$ppp_year.dta
	
	*Create yy variable, a year variable with two digits
	gen yy = year
	tostring yy, replace
	replace yy = substr(yy,-2,.)

	*Combine iso2 and yy to create ccyy, a country-year variable as the one identifying datasets
	egen ccyy = concat(iso2 yy)

	*Get distinct values of ccyy and call it countries_with_ppp
	qui levelsof ccyy, local(countries_with_ppp) clean
	
	tempfile ppp
	save "`ppp'"
}

*Selects the entire dataset or a small one for testing
if "$dataset" == "all" {
	qui lissydata, lis
}
else if "$dataset" == "test" {
	qui lissydata, lis from(2015) to(2020) iso2(cl uk za)
}

* Gets countries and the first country in the group
local countries "${selected}"
local first_country : word 1 of `countries'

*Gets first income/consumption variable in inc_cons_vars
local first_inc_cons : word 1 of $inc_cons_vars

*Gets first absolute poverty line in abs_povlines
local first_povline : word 1 of $abs_povlines

*Define an empty countries_without_ppp global macro
global countries_without_ppp

*Check countries in the income datasets not in PPP dataset
foreach c in `countries' {
	if !strpos("`countries_with_ppp'", "`c'") {
		global countries_without_ppp $countries_without_ppp `c'
	}
}

* Gets the data

foreach ccyy in `countries' {
	quietly use dhi dhci hifactor hiprivate hi33 hcexp hwgt hpopwgt nhhmem grossnet iso2 year using $`ccyy'h, clear
	
	*Merge with PPP data to get deflator (if PPPs are selected and only for countries with PPP data)
	if "$ppp_values" == "1" {
		quietly merge n:1 iso2 year using "`ppp'", keep(match) nogenerate keepusing(lisppp)
	}
	*Run make_variables function
	quietly make_variables
	
	* Option 1 is to get population, mean, median, gini and relative poverty variables
	if "$menu_option" == "1" {
		foreach var in $inc_cons_vars {
			
			quietly sum e`var'_b
			local n_`var' = r(N)
			
			if `n_`var'' > 0 {
			
				*For 40, 50, 60 (% of median)
				forvalues pct = 40(10)60 {
				
					*Calculate poverty metrics
					*If median DHI is selected
					if "$relative_poverty_dhi" == "1" {
						quietly povdeco e`var'_b [w=hwgt*nhhmem], pline(${povline_`pct'})
					}
					
					*If relative poverty is measured from the median of each welfare variable
					else if "$relative_poverty_dhi" == "0" {
						quietly povdeco e`var'_b [w=hwgt*nhhmem], pline(${povline_`pct'_`var'})
					}
					
					*fgt0 is headcount ratio
					local fgt0_`var'_`pct': di %9.2f r(fgt0) *100
					local fgt1_`var'_`pct': di %9.2f r(fgt1) *100
					local fgt2_`var'_`pct': di %9.4f r(fgt2)
					
					local meanpoor_`var'_`pct': di %9.2f r(meanpoor)
					local meangap_`var'_`pct': di %9.2f r(meangappoor)
				}
				
				*Calculate and store gini for equivalized income
				quietly ineqdec0 e`var'_b [w=hwgt*nhhmem]
				local gini_`var' : di %9.3f r(gini)
				
				*Get mean and median income
				local mean_`var': di %9.2f r(mean)
				local median_`var': di %9.2f r(p50)
			}
			
			else {
				
				*For 40, 50, 60 (% of median)
				forvalues pct = 40(10)60 {
					
					*fgt0 is headcount ratio
					local fgt0_`var'_`pct' = .
					local fgt1_`var'_`pct' = .
					local fgt2_`var'_`pct' = .
					
					local meanpoor_`var'_`pct' = .
					local meangap_`var'_`pct' = .
				}
				
				local gini_`var' = .
				
				*Get mean and median income
				local mean_`var' = .
				local median_`var' = .
			}

			*Print dataset header
			if "`ccyy'" == "`first_country'" & "`var'" == "`first_inc_cons'" di "dataset,variable,eq,pop,mean,median,gini,fgt0_40,fgt0_50,fgt0_60,fgt1_40,fgt1_50,fgt1_60,fgt2_40,fgt2_50,fgt2_60,meanpoor_40,meanpoor_50,meanpoor_60,meangap_40,meangap_50,meangap_60"
			*Print percentile thresholds and shares for each country, year, and income
			di "`ccyy',`var',$equivalized,$pop,`mean_`var'',`median_`var'',`gini_`var'',`fgt0_`var'_40',`fgt0_`var'_50',`fgt0_`var'_60',`fgt1_`var'_40',`fgt1_`var'_50',`fgt1_`var'_60',`fgt2_`var'_40',`fgt2_`var'_50',`fgt2_`var'_60',`meanpoor_`var'_40',`meanpoor_`var'_50',`meanpoor_`var'_60',`meangap_`var'_40',`meangap_`var'_50',`meangap_`var'_60'"
		}
	}
	
	* Option 2 is to get absolute poverty variables
	else if "$menu_option" == "2" {
		foreach var in $inc_cons_vars {
			
			quietly sum e`var'_b
			local n_`var' = r(N)
			
			foreach pline in $abs_povlines {
			
				if `n_`var'' > 0 {
			
					*Calculate poverty metrics
					local pline_year = `pline'/100*365
					quietly povdeco e`var'_b [w=hwgt*nhhmem], pline(`pline_year')
					
					*fgt0 is headcount ratio
					local fgt0_`var'_`pline': di %9.2f r(fgt0) *100
					local fgt1_`var'_`pline': di %9.2f r(fgt1) *100
					local fgt2_`var'_`pline': di %9.4f r(fgt2)
					
					local meanpoor_`var'_`pline': di %9.2f r(meanpoor)
					local meangap_`var'_`pline': di %9.2f r(meangappoor)
				}
				
				else {
				
					local fgt0_`var'_`pline' = .
					local fgt1_`var'_`pline' = .
					local fgt2_`var'_`pline' = .
					
					local meanpoor_`var'_`pline' = .
					local meangap_`var'_`pline' = .
				
				}
				
				*Print dataset header
				if "`ccyy'" == "`first_country'" & "`var'" == "`first_inc_cons'" & "`pline'" == "`first_povline'" di "dataset,variable,eq,povline,fgt0,fgt1,fgt2,meanpoor,meangap"
				*Print percentile thresholds and shares for each country, year, and income
				di "`ccyy',`var',$equivalized,`pline',`fgt0_`var'_`pline'',`fgt1_`var'_`pline'',`fgt2_`var'_`pline'',`meanpoor_`var'_`pline'',`meangap_`var'_`pline''"
				
			}
		}
	}

	* Option 3 is to get the deciles thresholds and shares of the income distribution
	else if "$menu_option" == "3" {
		foreach var in $inc_cons_vars {
		
			quietly sum e`var'_b
			local n_`var' = r(N)
			
			*Print dataset header
			if "`ccyy'" == "`first_country'" & "`var'" == "`first_inc_cons'" di "dataset,variable,eq,percentile,thr,share"
			
			if `n_`var'' > 0 {
			
				*Estimate percentile shares
				qui sumdist e`var'_b [w=hwgt*nhhmem], ngp(10)
				*Print percentile thresholds and shares for each country, year, and income
				forvalues j = 1/10 {
					local thr`j': di %16.2f r(q`j')
					local s`j': di %9.4f r(sh`j')*100
					local perc = `j'*10
					di "`ccyy',`var',$equivalized,`perc',`thr`j'',`s`j''"
				}
			}
			
			else {
			
				*Print percentile thresholds and shares for each country, year, and income
				forvalues j = 1/10 {
					local thr`j' = .
					local s`j' = .
					local perc = `j'*10
					di "`ccyy',`var',$equivalized,`perc',`thr`j'',`s`j''"
				}
			
			}
		}
	}
	* Option 4 is to get `grossnet' values, the variable that identifies if the dataset contains gross or net income and also the number of observations per dataset
	else if "$menu_option" == "4" {
		*Create unique values of grossnet (one per dataset)
		qui levelsof grossnet, local(uniq_gross) clean
		
		foreach var in $inc_cons_vars {
			
			quietly sum e`var'_b
			local n_`var' = r(N)
			
		}
		
		*Print dataset header
		if "`ccyy'" == "`first_country'" di "dataset,grossnet,n_dhi,n_dhci,n_mi,n_hcexp"
		di "`ccyy',`uniq_gross',`n_dhi',`n_dhci',`n_mi',`n_hcexp'"
	}
}
