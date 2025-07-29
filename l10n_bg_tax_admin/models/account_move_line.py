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

    @api.depends('balance')
    def _compute_l10n_bg_price_unit(self):
        for line in self:
            quantity = line.quantity == 0 and 1 or line.quantity
            line.l10n_bg_price_unit = line.balance / quantity
