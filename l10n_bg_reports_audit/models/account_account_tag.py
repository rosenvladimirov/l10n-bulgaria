#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

from .l10n_bg_file_helper import get_l10n_bg_applicability


class AccountAccountTag(models.Model):
    _inherit = ["account.account.tag", "l10n.bg.config.mixin"]
    _name = "account.account.tag"

    l10n_bg_applicability = fields.Selection(
        selection="_get_l10n_bg_applicability", string="Use for"
    )
    applicability = fields.Selection(
        selection_add=[
            ("l10n_bg_partner", "BG-NSI Usage for Partners"),
            ("l10n_bg_product", "BG-NSI Usage for Products")
        ],
        ondelete={
        "l10n_bg_partner": "set default",
        "l10n_bg_product": "set default"
        },
    )

    def _get_l10n_bg_applicability(self):
        return get_l10n_bg_applicability(self)
