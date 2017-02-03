from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        from main import tax_sheet as tax
        from main import test_tax_sheet as tst_tx

        tst_cls = tax.TaxUser(tst_tx.dob,
                              tst_tx.desired_retirement_age,
                              tst_tx.life_exp,
                              tst_tx.retirement_lifestyle,
                              tst_tx.reverse_mort,
                              tst_tx.house_value,
                              tst_tx.risk_profile_group,
                              tst_tx.filing_status,
                              tst_tx.total_income,
                              tst_tx.adj_gross_income,
                              tst_tx.taxable_income,
                              tst_tx.total_payments,
                              tst_tx.external_income,
                              tst_tx.income_growth,
                              tst_tx.employment_status,
                              tst_tx.ss_fra_todays,
                              tst_tx.ss_fra_retirement,
                              tst_tx.paid_days,
                              tst_tx.retirement_accounts,
                              tst_tx.zip_code)
    
        tst_cls.create_maindf()
        
