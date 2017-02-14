import logging
import pandas as pd
import numpy as np
import json
import math
from main import inflation
from main import us_tax
from main import tax_helpers as helpers
from main import test_tax_sheet as tst_tx
from main import abstract
from main import constants
from dateutil.relativedelta import relativedelta
from main import zip2state
from ssa import ssa as ssa
from rest_framework.exceptions import ValidationError
import pdb

logger = logging.getLogger('taxsheet')
inflation_level = inflation.inflation_level

NUM_US_RETIREMENT_ACCOUNT_TYPES = len(constants.US_RETIREMENT_ACCOUNT_TYPES)


class TaxUser(object):
    '''
    Contains a list of inputs and functions for Andrew's Excel tax sheet (Retirement Modelling v4.xlsx).
    '''
    def __init__(self,
                 dob,
                 desired_retirement_age,
                 life_exp,
                 retirement_lifestyle,
                 total_income,
                 reverse_mort,
                 house_value,
                 desired_risk,
                 filing_status,
                 tax_transcript_data,
                 plans,
                 income_growth,
                 employment_status,
                 ss_fra_todays,
                 paid_days,
                 retirement_accounts,
                 zip_code,
                 expenses,
                 btc):

        self.debug = True
        if (self.debug):
            helpers.show_inputs(dob,
                             desired_retirement_age,
                             life_exp,
                             retirement_lifestyle,
                             total_income,
                             reverse_mort,
                             house_value,
                             desired_risk,
                             filing_status,
                             tax_transcript_data,
                             plans,
                             income_growth,
                             employment_status,
                             ss_fra_todays,
                             paid_days,
                             retirement_accounts,
                             inflation_level,
                             zip_code,
                             expenses,
                             btc)

        adj_gross_income, total_payments, taxable_income = self.get_tax_transcript_data(tax_transcript_data)
        # adj_gross_income cannot be less than total_income
        adj_gross_income = helpers.validate_adj_gross_income(adj_gross_income, total_income)
  
        if not house_value:
            house_value = 0.
            
        if not ss_fra_todays:
            ss_fra_todays = 0.

        helpers.validate_inputs(dob,
                                 desired_retirement_age,
                                 life_exp,
                                 retirement_lifestyle,
                                 total_income,
                                 reverse_mort,
                                 house_value,
                                 desired_risk,
                                 filing_status,
                                 adj_gross_income,
                                 total_payments,
                                 taxable_income,
                                 plans,
                                 income_growth,
                                 employment_status,
                                 ss_fra_todays,
                                 paid_days,
                                 retirement_accounts,
                                 inflation_level,
                                 zip_code,
                                 expenses,
                                 btc)
        '''
        set variables
        '''
        self.dob = dob
        self.desired_retirement_age = desired_retirement_age
        self.life_exp = life_exp
        self.retirement_lifestyle = retirement_lifestyle
        self.reverse_mort = reverse_mort
        self.house_value = house_value
        self.desired_risk = desired_risk
        self.filing_status = abstract.PersonalData.CivilStatus(filing_status)
        self.total_income = total_income
        self.taxable_income = taxable_income
        self.plans = plans
        self.total_payments = total_payments
        self.other_income = max(0, adj_gross_income - total_income)
        self.income_growth = income_growth/100.
        self.employment_status = constants.EMPLOYMENT_STATUSES[employment_status]
        self.ss_fra_todays = ss_fra_todays
        self.paid_days = paid_days
        self.retirement_accounts = retirement_accounts
        self.contrib_rate_employee_401k = 0
        self.contrib_rate_employer_401k = 0
        self.initial_401k_balance = 0
        self.ira_rmd_factor = 26.5
        self.state = zip2state.get_state(zip_code)
        self.sum_expenses = helpers.get_sum_expenses(expenses)
        self.btc = btc

        '''
        age
        '''
        self.age = helpers.get_age(self.dob)
        self.validate_age()
        '''
        retirememt period
        '''
        self.validate_life_exp_and_des_retire_age()
        self.pre_retirement_end = helpers.get_period_of_age(self.age, self.desired_retirement_age)  # i.e. last period in which TaxUser is younger than desired retirement age                                                                                  # NB this period has index self.pre_retirement_end - 1
        self.retirement_start = self.pre_retirement_end + 1                                 # i.e. first period in which TaxUser is older than desired retirement age                                                                                   # NB this period has index self.retirement_start - 1

        '''
        years
        '''
        self.start_year = pd.Timestamp('today').year
        self.years_to_project = round(math.ceil(self.life_exp) - self.age) # i.e. assume user dies at the start of the year of their life expectancy, rather than at the ...
        self.retirement_years = round(math.ceil(self.life_exp) - self.desired_retirement_age)
        self.pre_retirement_years = round(self.desired_retirement_age - self.age)
        self.years = [i for i in range(self.start_year, self.start_year + self.years_to_project)]
        self.years_pre = [i for i in range(self.start_year, self.start_year + self.pre_retirement_years)]
        self.years_post = [i for i in range(self.start_year + self.pre_retirement_years, self.start_year + self.years_to_project)]

        '''
        remenant

        period to retirement may not be a whole number of years.
        'remenant' = periods representing this 'gap'
        '''
        self.remenant_periods = self.pre_retirement_end - (12 * len(self.years_pre))   
        self.remenant_start_index = (self.pre_retirement_years * 12) - 1 + 1 # i.e. we need the period AFTER the last pre-retirement period (so +1)
 
        '''
        rows
        '''
        self.total_rows = self.pre_retirement_end + (self.retirement_years * 12)
        
        '''
        annual inflation
        '''
        self.indices_for_inflation = [(11 + (i * 12)) for i in range(self.years_to_project)]
        if len(inflation_level) < self.indices_for_inflation[len(self.indices_for_inflation) - 1]:
            raise Exception("supplied inflation data does not cover the full period required")        
        self.annual_inflation = [sum(inflation_level[j*12:(j*12)+12])/12. for j in range(len(self.indices_for_inflation))]

        '''
        retirement_accounts
        '''
        self.init_balance, self.monthly_contrib_employee_base, self.monthly_contrib_employer_base = self.get_retirement_accounts()
        self.btc_factor = self.get_btc_factor(self.get_employee_monthly_contrib_monthly_view(), self.monthly_contrib_employee_base)

        '''
        dataframe indices
        '''
        self.dateind = helpers.get_retirement_model_projection_index(pd.Timestamp('today').date(), self.total_rows)
        self.dateind_pre = helpers.get_retirement_model_projection_index(pd.Timestamp('today').date(), self.pre_retirement_end)
        self.dateind_post = helpers.get_retirement_model_projection_index(self.dateind_pre[len(self.dateind_pre)-1], (self.total_rows - len(self.dateind_pre)))
        
        '''
        data frame
        '''
        self.maindf = pd.DataFrame(index=self.dateind)

                
    def create_maindf(self):
        '''
        create the main data frame
        '''
        self.maindf['Person_Age'] = [self.age + (1./12.)*(i+1) for i in range(self.total_rows)]

        # MONTHLY GROWTH RATE ASSUMPTIONS
        self.pre_proj_inc_growth_monthly = [self.income_growth/12. for i in range(self.pre_retirement_end)]
        self.post_proj_inc_growth_monthly = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.maindf['Proj_Inc_Growth_Monthly'] = self.set_full_series(self.pre_proj_inc_growth_monthly, self.post_proj_inc_growth_monthly)

        self.maindf['Proj_Inflation_Rate'] = helpers.get_inflator_to_period(self.total_rows)['Inflation_Rate']
        self.pre_proj_inflation_rate = [inflation_level[i]/12. for i in range(self.pre_retirement_end)] 
        self.post_proj_inflation_rate = [inflation_level[self.retirement_start + i]/12. for i in range(self.total_rows - self.pre_retirement_end)] 

        self.maindf['Portfolio_Return'] = self.maindf['Proj_Inflation_Rate'] + helpers.get_portfolio_return_above_cpi(self.desired_risk)/12.
        self.pre_portfolio_return = [inflation_level[i]/12. + helpers.get_portfolio_return_above_cpi(self.desired_risk)/12. for i in range(self.pre_retirement_end)]
        self.post_portfolio_return = [inflation_level[self.retirement_start + i]/12. + helpers.get_portfolio_return_above_cpi(self.desired_risk)/12.
                                      for i in range(self.total_rows - self.pre_retirement_end)]

        self.maindf['Retire_Work_Inc_Daily_Rate'] = [116*(1+self.income_growth/12.)**i for i in range(self.total_rows)]

        '''
        get the 'flators'
        '''
        self.pre_deflator = [0. for i in range(self.pre_retirement_end)]
        self.pre_deflator[self.pre_retirement_end - 1] = 1. * (1 - self.pre_proj_inflation_rate[self.pre_retirement_end - 1])                                                                                          
        for i in range (1, self.pre_retirement_end):
            self.pre_deflator[self.pre_retirement_end - 1 - i] = self.pre_deflator[self.pre_retirement_end - 1 - i + 1] * (1 - self.pre_proj_inflation_rate[self.pre_retirement_end - 1 - i])                                                                                         

        self.pre_inflator = [0. for i in range(self.pre_retirement_end)]
        self.pre_inflator[0] = 1. * (1 + self.pre_proj_inflation_rate[0])
        for i in range (1, self.pre_retirement_end):
            self.pre_inflator[i] = self.pre_inflator[i-1] * (1 + self.pre_proj_inflation_rate[i])

        self.post_inflator = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.post_inflator[0] = 1. * (1 + self.post_proj_inflation_rate[0])
        for i in range (1, self.total_rows - self.pre_retirement_end):
            self.post_inflator[i] = self.post_inflator[i - 1] * (1 + self.post_proj_inflation_rate[i])

        self.post_inflator_continuous = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.post_inflator_continuous[0] = self.pre_inflator[len(self.pre_inflator) -1] * (1 + self.post_proj_inflation_rate[0])
        for i in range (1, self.total_rows - self.pre_retirement_end):
            self.post_inflator_continuous[i] = self.post_inflator_continuous[i - 1] * (1 + self.post_proj_inflation_rate[i])
        
        self.maindf['Deflator'] = self.set_full_series(self.pre_deflator, [1. for i in range(self.total_rows - self.pre_retirement_end)])     # for pre-retirement
        self.maindf['Inflator'] = self.set_full_series([1. for i in range(self.pre_retirement_end)], self.post_inflator)                      # for post-retirement
        self.maindf['Flator'] = self.maindf['Deflator'] * self.maindf['Inflator']                                                             # deserves a pat on the back

        # INCOME RELATED - WORKING PERIOD
        '''
        get pre-retirement  income flator
        '''
        self.pre_df = pd.DataFrame(index=self.dateind_pre)
        self.pre_df['Inc_Growth_Monthly_Pre'] = self.maindf['Proj_Inc_Growth_Monthly'][0:self.pre_retirement_end]
        self.pre_df['Inc_Inflator_Pre'] = (1 + self.pre_df['Inc_Growth_Monthly_Pre']).cumprod()
        
        '''
        get pre-retirement inflation flator
        '''
        self.pre_df['Inf_Inflator_Pre'] = helpers.get_inflator_to_period(self.pre_retirement_end)['Inflator']

        self.pre_total_income = self.total_income/12. * self.pre_df['Inc_Inflator_Pre']
        self.post_total_income  = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.maindf['Total_Income'] = self.set_full_series(self.pre_total_income, self.post_total_income)
        
        self.pre_other_income = self.other_income/12. * self.pre_df['Inf_Inflator_Pre']
        self.post_other_income  = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.maindf['Other_Income'] = self.set_full_series(self.pre_other_income, self.post_other_income)                                

        self.maindf['Adj_Gross_Income'] = self.maindf['Total_Income'] + self.maindf['Other_Income']
        
        self.pre_fed_regular_tax = self.total_payments/12. * self.pre_df['Inf_Inflator_Pre']
        self.post_fed_regular_tax  = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.maindf['Fed_Regular_Tax_Est'] = self.set_full_series(self.pre_fed_regular_tax, self.post_fed_regular_tax)
        
        self.maindf['Fed_Taxable_Income'] = self.maindf['Adj_Gross_Income'] - self.maindf['Fed_Regular_Tax_Est']
        
        self.state_tax = us_tax.StateTax(self.state, self.filing_status, self.total_income)
        self.state_tax_after_credits = self.state_tax.get_state_tax()
        self.state_effective_rate_to_agi = self.state_tax_after_credits/self.total_income

        self.pre_state_tax_after_credits = self.state_tax_after_credits/12. * self.pre_df['Inf_Inflator_Pre']      
        self.post_state_tax_after_credits = [0. for i in range(self.total_rows - self.pre_retirement_end)]

        self.maindf['State_Tax_After_Credits'] = self.set_full_series(self.pre_state_tax_after_credits, self.post_state_tax_after_credits)
            
        self.maindf['After_Tax_Income_Est'] = self.maindf['Adj_Gross_Income'] - self.maindf['Fed_Regular_Tax_Est'] - self.maindf['State_Tax_After_Credits']
    
        fica_tx = us_tax.Fica(self.employment_status, self.total_income)
        self.fica_ss = fica_tx.get_for_ss()
        self.fica_medicare = fica_tx.get_for_medicare()
        self.fica = self.fica_ss + self.fica_medicare
        
        self.pre_fica = self.fica/12. * self.pre_df['Inf_Inflator_Pre']       
        self.post_fica = [0. for i in range(self.total_rows - self.pre_retirement_end)] 
        self.maindf['FICA'] = self.set_full_series(self.pre_fica, self.post_fica)

        self.maindf['Home_Value'] = self.house_value * (1+self.maindf['Proj_Inflation_Rate']).cumprod()

        # INCOME RELATED - ACCOUNTS
        self.maindf['All_Accounts'] = 0
        
        if self.retirement_accounts is not None:
            for acnt in self.retirement_accounts:
                k = helpers.get_retirement_account_index(acnt)
                self.maindf[str(k) + '_Employee'] = self.maindf['Total_Income'] * self.monthly_contrib_employee_base[k] * self.btc_factor[k]
                self.maindf[str(k) + '_Employer'] = self.maindf['Total_Income'] * self.monthly_contrib_employer_base[k] * self.btc_factor[k]
                pre_capital_growth, pre_balance = self.get_capital_growth_and_balance_series(self.pre_retirement_end, str(k), self.init_balance[k] )       
                post_balance = [pre_balance[self.pre_retirement_end - 1] for i in range(self.total_rows - self.pre_retirement_end)]
                post_capital_growth = [0. for i in range(self.total_rows - self.pre_retirement_end)]
                        
                for i in range(1, self.total_rows - self.pre_retirement_end): 
                    post_capital_growth[i] = (self.post_portfolio_return[i] * post_balance[i - 1]) 

                    if  post_capital_growth[i] + post_balance[i - 1] > 0:
                        post_balance[i] = post_capital_growth[i] + post_balance[i - 1]
                    else:
                        post_balance[i] = 0.

                self.maindf[str(k) + '_Capital_Growth'] = self.set_full_series(pre_capital_growth, post_capital_growth)
                self.maindf[str(k) + '_Balance'] = self.set_full_series(pre_balance, post_balance)
                self.maindf['All_Accounts'] = self.maindf['All_Accounts'] + self.maindf[str(k) + '_Balance']
                
        # NONTAXABLE ACCOUNTS
        # FOLLOWING NEEDS RE-WRITE; VERY FRAGILE ... WHAT IF ORDER OF THE ACCOUNTS IN constants:US_RETIREMENT_ACCOUNT_TYPES IS CHANGED?
        self.maindf['Nontaxable_Accounts_Pre_Deccumulation'] = 0

        if '9_Balance' in self.maindf:
            self.maindf['Nontaxable_AccountsPre_Deccumulation'] = self.maindf['Nontaxable_Accounts_Pre_Deccumulation'] + self.maindf['9_Balance']  # Ind Roth _401K

        if '19_Balance' in self.maindf:
            self.maindf['Nontaxable_Accounts_Pre_Deccumulation'] = self.maindf['Nontaxable_Accounts_Pre_Deccumulation'] + self.maindf['19_Balance'] # Roth IRA

        if '18_Balance' in self.maindf:
            self.maindf['Nontaxable_Accounts_Pre_Deccumulation'] = self.maindf['Nontaxable_Accounts_Pre_Deccumulation'] + self.maindf['18_Balance'] # Roth 401k

        # TAXABLE ACCOUNTS PRE DECCUMULATION
        self.maindf['Taxable_Accounts_Pre_Deccumulation'] = self.maindf['All_Accounts'] - self.maindf['Nontaxable_Accounts_Pre_Deccumulation']

        # CERTAIN INCOME
        if self.retirement_lifestyle == 1:
            self.lifestyle_factor = 0.66

        elif self.retirement_lifestyle == 2:
            self.lifestyle_factor = 0.81

        elif self.retirement_lifestyle == 3:
            self.lifestyle_factor = 1

        elif self.retirement_lifestyle == 4:
            self.lifestyle_factor = 1.5

        self.pre_des_ret_inc_pre_tax = self.lifestyle_factor * self.maindf['Adj_Gross_Income'][0:self.pre_retirement_end]
        self.post_des_ret_inc_pre_tax = [self.pre_des_ret_inc_pre_tax[len(self.pre_des_ret_inc_pre_tax) - 1] for i in range(self.total_rows - self.pre_retirement_end)] 
        self.maindf['Des_Ret_Inc_Pre_Tax_Post_Nominal'] = self.set_full_series(self.pre_des_ret_inc_pre_tax, self.post_des_ret_inc_pre_tax)
        self.maindf['Des_Ret_Inc_Pre_Tax'] = self.maindf['Des_Ret_Inc_Pre_Tax_Post_Nominal'] * self.maindf['Inflator']

        '''
        use the 'flators'
        '''
        self.maindf['Soc_Sec_Benefit'] = helpers.get_ss_fra_future_dollars(self.ss_fra_todays, self.total_rows) * helpers.get_soc_sec_factor(self.desired_retirement_age)
        
        self.maindf['Soc_Sec_Ret_Ear_Tax_Exempt'] = self.maindf['Soc_Sec_Benefit']

        self.maindf['Nominal_Ret_Working_Inc'] = np.where(self.maindf['Person_Age'] < 80, self.maindf['Retire_Work_Inc_Daily_Rate'] * 4 * self.paid_days, 0)
        self.maindf['Ret_Working_Inc'] = self.maindf['Deflator'] * self.maindf['Nominal_Ret_Working_Inc']
        
        self.maindf['Nominal_Pension_Payments'] = [0. for i in range(self.total_rows)]
        self.maindf['Pension_Payments'] = self.maindf['Deflator'] * self.maindf['Nominal_Pension_Payments']

        self.maindf['Annuity_Payments'] = self.get_all_retirement_income()

        # REVERSE MORTGAGE
        if self.reverse_mort:
            self.post_reverse_mortgage = np.where(self.age > 0,
                                                        np.where(self.maindf['Total_Income'] == 0,
                                                                 np.where(self.maindf['Person_Age'] > 62,
                                                                          self.maindf['Home_Value'][self.retirement_start - 1] * (0.9/(self.retirement_years * 12.)),
                                                                          0),
                                                                 0),
                                                        0)[self.pre_retirement_end:]

        else:
            self.post_reverse_mortgage = [0. for i in range(self.total_rows - self.pre_retirement_end)]
            
        self.pre_reverse_mortgage = [self.post_reverse_mortgage[0] for i in range (self.pre_retirement_end)]
        self.maindf['Reverse_Mortgage_Nominal'] = self.set_full_series(self.pre_reverse_mortgage, self.post_reverse_mortgage)
        self.maindf['Reverse_Mortgage'] = self.maindf['Deflator'] * self.maindf['Reverse_Mortgage_Nominal']

        # INCOME GAP
        self.maindf['Certain_Ret_Inc'] = self.get_full_post_retirement_and_pre_deflated(self.maindf['Soc_Sec_Benefit']
                                                                                        + self.maindf['Ret_Working_Inc']
                                                                                        + self.maindf['Pension_Payments']
                                                                                        + self.maindf['Annuity_Payments']
                                                                                        + self.maindf['Reverse_Mortgage'])
                                      
        self.maindf['Ret_Certain_Inc_Gap'] = self.get_full_post_retirement_and_pre_deflated(np.where(self.maindf['Des_Ret_Inc_Pre_Tax']- self.maindf['Certain_Ret_Inc'] > 0. ,
                                                                                                     self.maindf['Des_Ret_Inc_Pre_Tax']- self.maindf['Certain_Ret_Inc'], 0. ))

        # DECCUMULATIONS
        self.pre_deccumulation_capital_growth_nontaxable = [0. for i in range(self.pre_retirement_end)]
        self.pre_deccumulation_balance_nontaxable = [0. for i in range(self.pre_retirement_end)]  
        self.pre_deccumulation_capital_growth_taxable = [0. for i in range(self.pre_retirement_end)]
        self.pre_deccumulation_balance_taxable = [0. for i in range(self.pre_retirement_end)]       

        self.post_deccumulation_balance_nontaxable = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.post_deccumulation_capital_growth_nontaxable = [0. for i in range(self.total_rows - self.pre_retirement_end)]    
        self.post_deccumulation_balance_taxable = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.post_deccumulation_capital_growth_taxable = [0. for i in range(self.total_rows - self.pre_retirement_end)]

        self.reqd_min_dist = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.nontaxable_distribution = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        
        for i in range(0, self.total_rows - self.pre_retirement_end):
            self.post_deccumulation_capital_growth_nontaxable[i] = self.post_portfolio_return[i] * self.post_deccumulation_balance_nontaxable[i - 1] - self.nontaxable_distribution[i - 1]
            self.post_deccumulation_balance_nontaxable[i] = self.post_deccumulation_capital_growth_nontaxable[i] + self.post_deccumulation_balance_nontaxable[i - 1]

            if self.maindf['Person_Age'].iloc[self.pre_retirement_end + i] > 70.5:
                self.reqd_min_dist[i] = self.maindf['Taxable_Accounts_Pre_Deccumulation'].iloc[self.pre_retirement_end + i-1]/(self.ira_rmd_factor * 12.)
            else:
                self.reqd_min_dist[i] = 0.
                
            self.post_deccumulation_capital_growth_taxable[i] = self.post_portfolio_return[i] * self.post_deccumulation_balance_taxable[i - 1] - self.reqd_min_dist[i]
            self.post_deccumulation_balance_taxable[i] = self.post_deccumulation_capital_growth_taxable[i] + self.post_deccumulation_balance_taxable[i - 1]
                
            if self.maindf['Ret_Certain_Inc_Gap'].iloc[self.pre_retirement_end + i] > self.reqd_min_dist[i]:
                if self.maindf['Nontaxable_Accounts_Pre_Deccumulation'].iloc[self.pre_retirement_end + i] + self.post_deccumulation_balance_nontaxable[i] > 0:
                    self.nontaxable_distribution[i] = self.maindf['Ret_Certain_Inc_Gap'].iloc[self.pre_retirement_end + i] - self.reqd_min_dist[i]
                else:
                    self.nontaxable_distribution[i] = 0.

        self.maindf['Deccumulation_Capital_Growth_Taxable'] = self.set_full_series(self.pre_deccumulation_capital_growth_taxable, self.post_deccumulation_capital_growth_taxable)
        self.maindf['Deccumulation_Balance_Taxable'] = self.set_full_series(self.pre_deccumulation_balance_taxable, self.post_deccumulation_balance_taxable) 

        self.maindf['Deccumulation_Capital_Growth_Nontaxable'] = self.set_full_series(self.pre_deccumulation_capital_growth_nontaxable, self.post_deccumulation_capital_growth_nontaxable)
        self.maindf['Deccumulation_Balance_Nontaxable'] = self.set_full_series(self.pre_deccumulation_balance_nontaxable, self.post_deccumulation_balance_nontaxable)

        pre_zeros = [0. for i in range(self.pre_retirement_end)]
        self.maindf['Reqd_Min_Dist'] = self.set_full_series(pre_zeros, self.reqd_min_dist)
        self.maindf['Tot_Taxable_Dist'] = self.maindf['Reqd_Min_Dist']
        self.maindf['Tot_Nontaxable_Dist'] = self.set_full_series(pre_zeros, self.nontaxable_distribution)

        # TAXABLE ACCOUNTS POST-DECCUMULATION
        self.maindf['Taxable_Accounts'] = np.where(self.maindf['Taxable_Accounts_Pre_Deccumulation'] + self.maindf['Deccumulation_Balance_Taxable'] > 0,
                                                   self.maindf['Taxable_Accounts_Pre_Deccumulation'] + self.maindf['Deccumulation_Balance_Taxable'], 0)
        
        self.maindf['Nontaxable_Accounts'] = np.where(self.maindf['Nontaxable_Accounts_Pre_Deccumulation'] + self.maindf['Deccumulation_Balance_Nontaxable'] > 0,
                                                   self.maindf['Nontaxable_Accounts_Pre_Deccumulation'] + self.maindf['Deccumulation_Balance_Nontaxable'], 0)

        self.maindf['Ret_Inc_Gap'] = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Ret_Certain_Inc_Gap']
                                                                                     - self.maindf['Tot_Nontaxable_Dist']
                                                                                     - self.maindf['Tot_Taxable_Dist'])

        # CALCULATION OF AFTER TAX INCOME
        self.maindf['Non_Taxable_Inc'] = self.maindf['Tot_Nontaxable_Dist'] + self.maindf['Reverse_Mortgage']
        
        self.maindf['Taxable_Soc_Sec'] = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Soc_Sec_Benefit']
                                                                                        + self.maindf['Ret_Working_Inc']
                                                                                        + self.maindf['Pension_Payments']
                                                                                        + self.maindf['Annuity_Payments']
                                                                                        + self.maindf['Tot_Taxable_Dist']
                                                                                        - self.maindf['Soc_Sec_Ret_Ear_Tax_Exempt'])

        self.maindf['Tot_Inc'] = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Non_Taxable_Inc']
                                                                                + self.maindf['Tot_Taxable_Dist']
                                                                                + self.maindf['Annuity_Payments']
                                                                                + self.maindf['Pension_Payments']
                                                                                + self.maindf['Ret_Working_Inc']
                                                                                + self.maindf['Soc_Sec_Benefit'])

        self.taxable_inc_pre = (self.maindf['Soc_Sec_Benefit']
                                + self.maindf['Ret_Working_Inc']
                                + self.maindf['Pension_Payments']
                                + self.maindf['Annuity_Payments']
                                + self.maindf['Tot_Taxable_Dist'])[:self.pre_retirement_end]

        self.taxable_inc_post = (self.maindf['Taxable_Soc_Sec']
                                 + self.maindf['Ret_Working_Inc']
                                 + self.maindf['Pension_Payments']
                                 + self.maindf['Annuity_Payments']
                                 + self.maindf['Tot_Taxable_Dist'])[self.pre_retirement_end:]
        
        self.maindf['Taxable_Inc'] = self.set_full_series(self.taxable_inc_pre, self.taxable_inc_post)

        self.maindf['Adj_Gross_Inc'] = self.maindf['Tot_Inc']

        '''
        federal tax
        '''
        self.maindf['Fed_Taxable_Inc'] = self.set_full_series([0. for i in range(self.pre_retirement_end)], self.maindf['Taxable_Inc'][self.pre_retirement_end:])

        self.annual_taxable_income_pre = [self.maindf['Fed_Taxable_Income'][(i * 12)]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 1]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 2]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 3]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 4]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 5]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 6]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 7]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 8]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 9]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 10]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 11] for i in range(self.pre_retirement_years)]

        for i in range(self.remenant_periods):
            self.annual_taxable_income_pre = self.maindf['Fed_Taxable_Income'][self.remenant_start_index -1 + i]
        
        self.annual_taxable_income_post = [self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12)]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 1]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 2]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 3]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 4]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 5]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 6]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 7]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 8]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 9]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 10]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 11] for i in range(self.retirement_years)]
       
        self.annual_taxable_income = self.set_full_series_with_indices(self.annual_taxable_income_pre,
                                                                       self.annual_taxable_income_post,
                                                                       self.years_pre,
                                                                       self.years_post)

        taxFed = us_tax.FederalTax(self.filing_status,
                                   self.years,
                                   self.annual_inflation,
                                   self.annual_taxable_income)
        taxFed.create_tax_engine()
        taxFed.create_tax_projected()

        self.annual_projected_tax = taxFed.tax_projected['Projected_Fed_Tax'] 
        self.post_projected_tax = pd.Series()
        
        for i in range(len(self.years_post)):
            self.post_projected_tax = self.post_projected_tax.append(pd.Series([self.annual_projected_tax.iloc[self.pre_retirement_years - 1  + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1  + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1  + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years- 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years- 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.],
                                                                               index = [self.dateind_post[i * 12],
                                                                               self.dateind_post[(i * 12) + 1],
                                                                               self.dateind_post[(i * 12) + 2],
                                                                               self.dateind_post[(i * 12) + 3],
                                                                               self.dateind_post[(i * 12) + 4],
                                                                               self.dateind_post[(i * 12) + 5],
                                                                               self.dateind_post[(i * 12) + 6],
                                                                               self.dateind_post[(i * 12) + 7],
                                                                               self.dateind_post[(i * 12) + 8],
                                                                               self.dateind_post[(i * 12) + 9],
                                                                               self.dateind_post[(i * 12) + 10],
                                                                               self.dateind_post[(i * 12) + 11]]))

        
        full_post = pd.Series(self.post_projected_tax, index=self.dateind_post) 
        self.maindf['Fed_Regular_Tax'] = self.set_full_series([0. for i in range(self.pre_retirement_end)], self.post_projected_tax )
        self.maindf['State_Tax_After_Credits'] = self.maindf['Adj_Gross_Inc'] * self.state_effective_rate_to_agi
        self.maindf['After_Tax_Income'] = self.maindf['Adj_Gross_Inc'] - self.maindf['Fed_Regular_Tax'] - self.maindf['State_Tax_After_Credits']

        # ACTUAL INCOME
        self.maindf['Actual_Inc'] = self.maindf['Total_Income'] + self.maindf['Tot_Inc']

        # DESIRED INCOME
        self.pre_0 = [0 for i in range(self.pre_retirement_end)]
        self.maindf['Desired_Inc'] = self.set_full_series(self.pre_0, self.post_des_ret_inc_pre_tax) * self.maindf['Inflator']

        # DEFLATION FACTOR AT RETIREMENT IN TODAYS
        self.deflation_factor_retirement_in_todays = helpers.get_inflator_to_period(self.retirement_start)['Inflator'][self.retirement_start - 1]

        # PROJECTED BALANCE AT RETIREMENT IN TODAYS
        self.projected_balance_at_retirement_in_todays = self.maindf['Taxable_Accounts'][self.retirement_start]/self.deflation_factor_retirement_in_todays

        # PROJECTED INCOME ACTUAL AT RETIREMENT IN TODAYS
        self.projected_income_actual_at_retirement_in_todays = self.maindf['Tot_Inc'][self.retirement_start]/self.deflation_factor_retirement_in_todays

        # PROJECTED INCOME DESIRED AT RETIREMENT IN TODAYS
        self.projected_income_desired_at_retirement_in_todays = self.maindf['Desired_Inc'][self.retirement_start]/self.deflation_factor_retirement_in_todays

        # SAVINGS END DATE AS AGE 
        self.savings_end_date_as_age = self.get_savings_end_date_as_age()

        # SOA DOLLAR BILL PERCENTAGES CURRENT
        self.soc_sec_percent_current, self.medicare_percent_current, self.fed_tax_percent_current, self.state_tax_percent_current = self.get_soa_dollar_bill_percentages()

        # COMPONENTS OF TAXABLE INCOME
        self.non_taxable_inc = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Non_Taxable_Inc'])
        self.tot_taxable_dist = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Tot_Taxable_Dist'])
        self.annuity_payments = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Annuity_Payments'])
        self.pension_payments = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Pension_Payments'])
        self.ret_working_inc = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Ret_Working_Inc'])
        self.soc_sec_benefit = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Soc_Sec_Benefit'])

        # COMPONENTS OF ACCOUNTS
        self.taxable_accounts = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Taxable_Accounts']) 
        self.non_taxable_accounts = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Nontaxable_Accounts'])
        
        if(self.debug):
            self.show_outputs()
            

    def get_a_retirement_income(self, begin_date, amount):
        '''
        returns self.maindf['This_Annuity_Payments'] determined from retirement income.
        '''
        self.maindf['This_Annuity_Payments_Nominal'] = 0
        try:
            months_to_annuity_start = math.ceil(((pd.Timestamp(begin_date) - pd.Timestamp('today')).days) * (12./365.25))
            if months_to_annuity_start > 0 and months_to_annuity_start < self.total_rows:
                pre_ret_inc = [0. for i in range(months_to_annuity_start)]
                post_ret_inc_nominal = [amount for i in range(self.total_rows - months_to_annuity_start)]
                dateind_pre_annuity = [pd.Timestamp('today').date() + relativedelta(months=1) + relativedelta(months=+i) for i in range(months_to_annuity_start)]
                dateind_post_annuity = [dateind_pre_annuity[len(dateind_pre_annuity)-1] + relativedelta(months=1) + relativedelta(months=+i) for i in range(self.total_rows - months_to_annuity_start)]
                self.maindf['This_Annuity_Payments_Nominal'] = self.maindf['This_Annuity_Payments_Nominal'] + self.set_full_series_with_indices(pre_ret_inc, post_ret_inc_nominal, dateind_pre_annuity, dateind_post_annuity)
            return self.maindf['This_Annuity_Payments_Nominal'] * (1 + self.maindf['Proj_Inflation_Rate']).cumprod()
        except:
            return 0


    def get_all_retirement_income(self):
        '''
        returns self.maindf['Annuity_Payments'], the sum of all retirment incomes.
        '''
        self.maindf['All_Annuity_Payments'] = 0
        retirement_income_details = []
        retirement_income_details = self.get_retirement_income_details_from_plans()
        for detail in retirement_income_details:
            self.maindf['All_Annuity_Payments'] = self.get_a_retirement_income(detail[0], detail[1])
        return self.maindf['All_Annuity_Payments']


    def get_btc_factor(self, employee_monthly_contrib_monthly_view, monthly_contrib_employee_base):
        '''
        'btc factor' is multiplied by all retirement account contributions to incorporate effect of varying proportions in Monthly View pie chart. 
        '''
        btc_factor = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        if self.retirement_accounts is not None:
            for acnt in self.retirement_accounts:
                j = helpers.get_retirement_account_index(acnt)
                if monthly_contrib_employee_base[j] == 0:
                    btc_factor[j] = 0.
                else:
                    btc_factor[j] = (employee_monthly_contrib_monthly_view/monthly_contrib_employee_base[j])
        pdb.set_trace()
        return btc_factor


    def get_capital_growth_and_balance_series(self, period, account_type, starting_balance):
        '''
        returns capital growth and balance series over period for account_tyconstants.US_RETIREMENT_ACCOUNT_TYPEpe
        '''
        '''
        for now can't think of a more 'pythonic' way to do this next bit ... may need re-write ...
        '''
        balance = [starting_balance for i in range(period)]
        capital_growth = [0. for i in range(period)]
        for i in range(1, period):
            capital_growth[i] = self.maindf['Portfolio_Return'][i] * balance[i - 1]
            balance[i] = self.maindf[account_type + '_Employee'][i] + self.maindf[account_type + '_Employer'][i] + capital_growth[i] + balance[i - 1]
        return capital_growth, balance


    def get_employee_monthly_contrib_monthly_view(self):
        '''
        returns monthly contriburion for employee based on monthly view pie chart
        '''
        return max(0, (self.total_income/12. - self.sum_expenses)/(self.total_income/12.))
        # NB - both following quantities are annual
        # return (self.btc/self.total_income) 
    

    def get_full_post_retirement_and_pre_deflated(self, temp_df_column):
        '''
        returns data frame column having 'real' (c.f. 'nominal') vales, where post retirement is calculated
        from other columns, and pre-retirement is the deflated retirement value
        '''
        nominal_pre = [temp_df_column[self.pre_retirement_end - 1] for i in range(self.pre_retirement_end)]
        real_post = [temp_df_column[self.retirement_start - 1 + i] for i in range(self.total_rows - self.pre_retirement_end)]
        result = self.maindf['Deflator'] * self.set_full_series(nominal_pre, real_post)
        return result
    

    def get_full_post_retirement_and_pre_set_zero(self, temp_df_column):
        '''
        returns data frame column having 'real' (c.f. 'nominal') values, where post retirement is calculated
        from other columns, and pre-retirement is set to zero
        '''
        nominal_pre = [0. for i in range(self.pre_retirement_end)]
        real_post = [temp_df_column[self.retirement_start - 1 + i] for i in range(self.total_rows - self.pre_retirement_end)]
        result = self.set_full_series(nominal_pre, real_post)
        return result
    

    def get_full_pre_retirement_and_post_set_zero(self, temp_df_column):
        '''
        returns data frame column having 'real' (c.f. 'nominal') values, where pre retirement is calculated
        from other columns, and post-retirement is set to zero
        '''
        nominal_pre = [temp_df_column[self.pre_retirement_end - 1] for i in range(self.pre_retirement_end)]
        real_post = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        result = self.set_full_series(nominal_pre, real_post)
        return result
    

    def set_full_series(self, series_pre, series_post):
        '''
        returns full series by appending pre-retirement and post-retirement series
        '''
        full_pre = pd.Series(series_pre, index=self.dateind_pre)
        full_post = pd.Series(series_post, index=self.dateind_post)
        result = full_pre.append(full_post)
        return result


    def get_period_as_age(self, period):
        '''
        returns age corresponding to period
        '''
        if period < 0:
            raise Exception('period < 0')
        return self.age + (period/12.)
            
    
    def get_retirement_accounts(self):
        '''
        returns lists of initial balances and monthly employee and employer contribution percentages, indexed according to constants.US_RETIREMENT_ACCOUNT_TYPES
        '''
        init_balance = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        monthly_contrib_amt_employee = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        employer_match_contributions = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        employer_match_income = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        
        if self.retirement_accounts is not None:
            for acnt in self.retirement_accounts:
                i = helpers.get_retirement_account_index(acnt)
                init_balance[i] = init_balance[i] + acnt['balance']

                if acnt['contrib_amt'] > 0:
                    if acnt['contrib_period'] == 'monthly':
                        monthly_contrib_amt_employee[i] = monthly_contrib_amt_employee[i] + acnt['contrib_amt']
                    else:
                        monthly_contrib_amt_employee[i] = monthly_contrib_amt_employee[i] + acnt['contrib_amt']/12.

                if acnt['employer_match_type'] == 'contributions':
                    employer_match_contributions[i] = employer_match_contributions[i] + acnt['employer_match']
                else:
                    employer_match_income[i] = employer_match_income[i] + acnt['employer_match']
                    
        monthly_contrib_employee_base = [(monthly_contrib_amt_employee[i]/(self.total_income/12.)) for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]           
        monthly_contrib_employer_base = [(employer_match_income[i] + (employer_match_contributions[i] * monthly_contrib_employee_base[i])) for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)] 
        return init_balance, monthly_contrib_employee_base, monthly_contrib_employer_base
        

    def get_retirement_income_details_from_plans(self):
        '''
        returns a list of tuples (begin_date, monthly amount) for each source of external_income in plans  
        '''
        external_income = []

        for plan in self.plans:
            try:
                if plan.external_income.all() != []:
                    begin_date = plan.external_income.all()[0].begin_date
                    amount = plan.external_income.all()[0].amount
                    detail = (begin_date, amount)
                    external_income.append(detail)
            except:
                if (self.debug):
                    print(str(plan) + " not of expected form")
        return external_income 


    def get_savings_end_date_as_period(self):
        '''
        returns period post retirement when taxable assets first deplete to zero
        '''
        for i in range(self.retirement_start, self.total_rows):
            if self.maindf['Taxable_Accounts'][i] == 0:
                return i
        return self.total_rows
                

    def get_savings_end_date_as_age(self):
        '''
        returns age post retirement when taxable assets first deplete to zero
        '''
        age = self.get_period_as_age(self.get_savings_end_date_as_period())
        if age < self.desired_retirement_age:
            raise Exception('age < self.desired_retirement_age')


    def get_soa_dollar_bill_percentages(self):
        '''
        returns current day social security payment, medicare payment, federal income
        tax payment, and state income tax payment all as a percentrage of current income
        '''
        if not self.total_income:
            raise Exception('self.total_income is None')

        if self.total_income == 0:
            return 0, 0, 0, 0
            
        if not self.fica_ss:
            raise Exception('self.fica_ss is None')
        soc_sec_percent = self.fica_ss/self.total_income
        
        if not self.fica_medicare:
            raise Exception('self.fica_medicare is None')
        medicare_percent = self.fica_medicare/self.total_income
        
        fed_tax_percent = self.annual_projected_tax.iloc[0]/self.total_income

        # self.pre_state_tax_after_credits is a monthly figure
        state_tax_percent = (12 * self.pre_state_tax_after_credits.iloc[0])/self.total_income

        if soc_sec_percent + medicare_percent + fed_tax_percent + state_tax_percent <= 1:
            return soc_sec_percent, medicare_percent, fed_tax_percent, state_tax_percent

        else:
            raise Exception('soc_sec_percent + medicare_percent + fed_tax_percent + state_tax_percent > 1')
        return age
    

    def get_tax_transcript_data(self, tax_transcript_data):
        '''
        returns adj_gross_income, total_payments, taxable_income
        '''
        try:
            adj_gross_income = tax_transcript_data['adjusted_gross_income']
        except:
            adj_gross_income = 0

        try:
            total_payments = tax_transcript_data['total_payments']
        except:
            total_payments = 0

        try:
            taxable_income = tax_transcript_data['taxable_income']
        except:
            taxable_income = 0

        return adj_gross_income, total_payments, taxable_income


    def set_full_series_with_indices(self, series_pre, series_post, index_pre, index_post):
        '''
        returns full series by appending pre-retirement series (with index2) and post-retirement
        series (with index2) 
        '''       
        full_pre = pd.Series(series_pre, index_pre)
        full_post = pd.Series(series_post, index_post)
        result = full_pre.append(full_post)
        return result

    
    def show_outputs(self):
        start = max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 10)
        end = min(max(helpers.get_period_of_age(self.age, 71) , start + 1) ,self.total_rows)
        print("--------------------------------------Retirement model OUTPUTS -------------------")
        print("--------------------------------------Taxable_Accounts ---------------------------")
        print(self.maindf['Taxable_Accounts'][start:end])
        print("--------------------------------------Taxable_Accounts_Pre_Deccumulation ---------------------------")
        print(self.maindf['Taxable_Accounts_Pre_Deccumulation'][start:end])
        print("--------------------------------------Nontaxable_Accounts ---------------------------")
        print(self.maindf['Nontaxable_Accounts'][start:end])
        print("--------------------------------------Nontaxable_Accounts_Pre_Deccumulation ---------------------------")
        print(self.maindf['Nontaxable_Accounts_Pre_Deccumulation'][start:end])
        print("--------------------------------------Actual_Inc ---------------------------")
        print(self.maindf['Actual_Inc'][start:end])
        print("--------------------------------------Non_Taxable_Inc ---------------------------")
        print(self.maindf['Non_Taxable_Inc'][start:end])
        print("--------------------------------------Tot_Taxable_Dist ---------------------------")
        print(self.maindf['Tot_Taxable_Dist'][start:end])
        print("--------------------------------------Annuity_Payments ---------------------------")
        print(self.maindf['Annuity_Payments'][start:end])
        print("--------------------------------------Pension_Payments ---------------------------")
        print(self.maindf['Pension_Payments'][start:end])
        print("--------------------------------------Ret_Working_Inc ---------------------------")
        print(self.maindf['Ret_Working_Inc'][start:end])
        print("--------------------------------------Soc_Sec_Benefit ---------------------------")
        print(self.maindf['Soc_Sec_Benefit'][start:end])
        print("--------------------------------------Desired_Inc ---------------------------")
        print(self.maindf['Desired_Inc'][start:end])
        print("--------------------------------------Ret_Certain_Inc_Gap ---------------------------")
        print(self.maindf['Ret_Certain_Inc_Gap'][start:end])
        print("--------------------------------------Ret_Inc_Gap ---------------------------")
        print(self.maindf['Ret_Inc_Gap'][start:end])
        print("--------------------------------------Reqd_Min_Dist ---------------------------")
        print(self.maindf['Reqd_Min_Dist'][start:end])
        print("--------------------------------------Person_Age ---------------------------")
        print(self.maindf['Person_Age'][start:end])
        print("--------------------------------------Various ---------------------------")
        print('self.age:                    ' + str(self.age))
        print('self.savings_end_date_as_age:' + str(self.savings_end_date_as_age))
        print('self.soc_sec_percent_current ' + str(self.soc_sec_percent_current))
        print('self.medicare_percent_current' + str(self.medicare_percent_current))
        print('self.fed_tax_percent_current ' + str(self.fed_tax_percent_current))
        print('self.state_tax_percent_current:' + str(self.state_tax_percent_current))
        print('ss_fra_retirement:           ' + str(helpers.get_ss_benefit_future_dollars(self.ss_fra_todays, self.dob, self.desired_retirement_age)))
        print("[Set self.debug=False to hide these]")
            

    def validate_age(self):
        if self.age >= self.desired_retirement_age:
            raise Exception("age greater than or equal to desired retirement age")

        if self.age <= 0:
            raise Exception("age less than or equal to 0")


    def validate_life_exp_and_des_retire_age(self):
        if self.life_exp > 100:
            raise Exception("self.life_exp > 100")
            
        if self.life_exp < 65:
            raise Exception("self.life_exp < 65")
        '''
        model requires at least one period (i.e. one month) between retirement_age and life_expectancy
        '''
        if self.life_exp == self.desired_retirement_age:
            self.life_exp = self.life_exp + 1
