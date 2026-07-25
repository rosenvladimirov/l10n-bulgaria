#  Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.account.models.account_account import AccountAccount as accountaccount
from odoo.addons.account.models.account_move_line import (
    AccountMoveLine as accountmoveline,
)
from odoo.addons.account.models.chart_template import (
    AccountChartTemplate as accountcharttemplate,
)
from odoo.addons.account.models.company import ResCompany as rescompany

from .models.account_account import AccountAccount
from .models.account_move_line import (
    AccountMoveLine as AccountMoveLine,
)
from .models.chart_template import AccountChartTemplate
from .models.company import ResCompany as ResCompany


def post_load_hook():
    accountaccount._search_new_account_code = AccountAccount._search_new_account_code
    accountcharttemplate._prepare_transfer_account_template = AccountChartTemplate._prepare_transfer_account_template
    accountcharttemplate._create_liquidity_journal_suspense_account = AccountChartTemplate._create_liquidity_journal_suspense_account
    accountcharttemplate._create_cash_discount_loss_account = AccountChartTemplate._create_cash_discount_loss_account
    accountcharttemplate._create_cash_discount_gain_account = AccountChartTemplate._create_cash_discount_gain_account
    accountcharttemplate.generate_fiscal_position = AccountChartTemplate.generate_fiscal_position
    accountcharttemplate._get_template_ref = AccountChartTemplate._get_template_ref
    accountcharttemplate._get_templates = AccountChartTemplate._get_templates
    rescompany.get_unaffected_earnings_account = ResCompany.get_unaffected_earnings_account
    accountmoveline._compute_all_tax = AccountMoveLine._compute_all_tax
