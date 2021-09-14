# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_bg_extend = fields.Boolean(
        'Bulgaria - Accounting extend',
        help='Provide all needed functionality for Bulgarian.\n'
             'Accounting and law documents.'
    )
    module_l10n_bg_account_financial_report = fields.Boolean(
        'Bulgaria - Account Financial Reports',
        help='Provide all reports for Bulgarian accounting.'
    )
    module_l10n_bg_intrastat_product = fields.Boolean(
        'Bulgaria - Intrastat Product Declaration',
        help='Provide Intrastat Product Declaratio.'
    )
    module_l10n_bg_account_voucher = fields.Boolean(
        'Bulgaria - Accounting voucher',
        help='This is the module to manage the Accounting Vouchers.\n'
        'Extend account voucher (tickets) to make simply invoices.'
    )
    module_l10n_bg_vat_period_gensoft = fields.Boolean(
        'Bulgaria - Use different period for VAT',
        help='Split vendor bill to use VAT credit in different period.'
    )
    module_l10n_bg_fleet_waybill = fields.Boolean(
        'Bulgaria - Vehicle Waybill',
        help='This is the module add waybill for Bulgaria with stock move.'
    )
    module_l10n_bg_hr_expense = fields.Boolean(
        'Bulgaria - Accounting Expense Tracker',
        help='This is the module to manage the Accounting Expense Tracker.'
    )
