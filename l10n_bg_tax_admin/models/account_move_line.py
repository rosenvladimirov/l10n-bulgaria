# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_bg_price_unit = fields.Monetary(
        string='Unit price currency (balance)',
        compute='_compute_l10n_bg_price_unit', store=True, readonly=False,
        currency_field='company_currency_id',
        tracking=True,
    )

    # Митнически данни
    l10n_bg_is_customs_expense = fields.Boolean(
        related='product_id.l10n_bg_is_customs_expense',
        store=True
    )
    l10n_bg_customs_value = fields.Monetary(
        string='Customs Value',
        currency_field='currency_id'
    )

    # Количествена информация
    l10n_bg_weight_net = fields.Float(string='Net Weight (kg)')
    l10n_bg_weight_gross = fields.Float(string='Gross Weight (kg)')
    l10n_bg_package_type = fields.Selection([
        ('box', 'Box'),
        ('pallet', 'Pallet'),
        ('container', 'Container'),
        ('bag', 'Bag'),
        ('barrel', 'Barrel'),
        ('other', 'Other')
    ], string='Package Type')
    l10n_bg_number_of_packages = fields.Integer(string='Number of Packages')

    # Тарифна информация
    l10n_bg_tariff_rate = fields.Float(string='Tariff Rate (%)')
    l10n_bg_calculated_duty = fields.Monetary(
        string='Calculated Duty',
        currency_field='currency_id',
        compute='_compute_customs_amounts'
    )

    @api.depends('l10n_bg_customs_value', 'l10n_bg_tariff_rate')
    def _compute_customs_amounts(self):
        for line in self:
            line.calculated_duty = line.l10n_bg_customs_value * (line.l10n_bg_tariff_rate / 100.0)

    @api.depends('balance')
    def _compute_l10n_bg_price_unit(self):
        for line in self:
            quantity = line.quantity == 0 and 1 or line.quantity
            line.l10n_bg_price_unit = line.balance / quantity
