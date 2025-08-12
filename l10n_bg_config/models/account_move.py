#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = ["account.move", "l10n.bg.config.mixin"]
    _name = "account.move"

    l10n_bg_name = fields.Char(
        "Number of locale document",
        index="trigram",
        tracking=True,
        copy=False
    )
    l10n_bg_date = fields.Date("Date of locale document", copy=False)
    l10n_bg_deal_date = fields.Date("Date of deal", copy=False, compute='_compute_l10n_bg_deal_date', store=True)

    @api.depends("invoice_date", "date")
    def _compute_l10n_bg_deal_date(self):
        for move in self:
            move.l10n_bg_deal_date = move.invoice_date or move.date
