#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment, SUPERUSER_ID

from odoo.addons.l10n_bg_tax_admin.models.account_account import AccountAccount
from odoo.addons.l10n_bg_tax_admin.models.chart_template import AccountChartTemplate
from odoo.addons.account.models.account_account import AccountAccount as accountaccount
from odoo.addons.account.models.chart_template import AccountChartTemplate as accountcharttemplate


def pre_init_hook(cr):
    env = Environment(cr, SUPERUSER_ID, {})
    #  mark fiscal position to update
    fiscal_position = env['ir.model.data'].search([
        ('module', '=', 'l10n_bg'),
        ('model', '=', 'account.fiscal.position.template')
    ])
    taxes = env['ir.model.data'].search([
        ('module', '=', 'l10n_bg'),
        ('model', '=', 'account.tax.template')
    ])
    for fp in fiscal_position + taxes:
        fp.update({
            'noupdate': False,
        })


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    fiscal_position = env['ir.model.data'].search([
        ('module', '=', 'l10n_bg_tax_admin'),
        ('model', '=', 'account.fiscal.position.template')
    ])
    taxes = env['ir.model.data'].search([
        ('module', '=', 'l10n_bg_tax_admin'),
        ('model', '=', 'account.tax.template')
    ])
    # for fp in fiscal_position + taxes:
    #     fp.update({
    #         'module': 'l10n_bg',
    #     })


def post_load_hook():
    accountaccount._search_new_account_code = AccountAccount._search_new_account_code
    accountcharttemplate._prepare_transfer_account_template = AccountChartTemplate._prepare_transfer_account_template
    accountcharttemplate._create_liquidity_journal_suspense_account = AccountChartTemplate._create_liquidity_journal_suspense_account
    accountcharttemplate._create_cash_discount_loss_account = AccountChartTemplate._create_cash_discount_loss_account
    accountcharttemplate._create_cash_discount_gain_account = AccountChartTemplate._create_cash_discount_gain_account
    accountcharttemplate.generate_fiscal_position = AccountChartTemplate.generate_fiscal_position
