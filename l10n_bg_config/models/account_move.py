#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = ["account.move", "l10n.bg.config.mixin"]
    _name = "account.move"

    l10n_bg_name = fields.Char(
        "Number of locale document", index="trigram", tracking=True, copy=False
    )
    l10n_bg_date = fields.Date("Date of locale document", copy=False)
