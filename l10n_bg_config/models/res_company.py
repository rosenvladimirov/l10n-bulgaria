# -*- coding: utf-8 -*-
#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # l10n_bg_property_account_receivable_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_account_receivable_id')
    # l10n_bg_property_account_payable_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_account_payable_id')
    # l10n_bg_property_account_expense_categ_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_account_expense_categ_id')
    # l10n_bg_property_account_income_categ_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_account_income_categ_id')
    # l10n_bg_expense_currency_exchange_account_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.expense_currency_exchange_account_id')
    # l10n_bg_income_currency_exchange_account_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.income_currency_exchange_account_id')
    # l10n_bg_property_tax_payable_account_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_tax_payable_account_id')
    # l10n_bg_property_tax_receivable_account_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_tax_receivable_account_id')

    l10n_bg_uic = fields.Char('Unique identification code', related='partner_id.l10n_bg_uic')
    l10n_bg_uic_type = fields.Selection(string='Type of Bulgaria UID',
                                        related='partner_id.l10n_bg_uic_type',
                                        help="Choice type of Bulgaria UID.")
    l10n_bg_departament_code = fields.Integer("Departament code")
    l10n_bg_tax_contact_id = fields.Many2one('res.partner',
                                             string='TAX Report creator')

    @api.depends('vat')
    def _onchange_vat(self):
        self.partner_id._check_l10n_bg_uic()

