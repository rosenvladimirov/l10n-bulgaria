#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment, SUPERUSER_ID

from odoo.addons.l10n_bg_tax_admin.models.account_account import AccountAccount
from odoo.addons.l10n_bg_tax_admin.models.chart_template import AccountChartTemplate
from odoo.addons.account.models.account_account import AccountAccount as accountaccount
from odoo.addons.account.models.chart_template import AccountChartTemplate as accountcharttemplate


def post_load_hook():
    accountaccount._search_new_account_code = AccountAccount._search_new_account_code
    accountcharttemplate._prepare_transfer_account_template = AccountChartTemplate._prepare_transfer_account_template
    accountcharttemplate._create_liquidity_journal_suspense_account = AccountChartTemplate._create_liquidity_journal_suspense_account
    accountcharttemplate._create_cash_discount_loss_account = AccountChartTemplate._create_cash_discount_loss_account
    accountcharttemplate._create_cash_discount_gain_account = AccountChartTemplate._create_cash_discount_gain_account
    accountcharttemplate.generate_fiscal_position = AccountChartTemplate.generate_fiscal_position
