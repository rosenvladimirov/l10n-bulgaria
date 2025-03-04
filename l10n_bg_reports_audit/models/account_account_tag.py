#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

from .l10n_bg_file_helper import get_l10n_bg_applicability


class AccountAccountTag(models.Model):
    _inherit = ["account.account.tag", "l10n.bg.config.mixin"]
    _name = "account.account.tag"

    l10n_bg_applicability = fields.Selection(
        selection=get_l10n_bg_applicability(), string="Use for"
    )
    l10n_bg_code = fields.Char(
        "Code", compute="_compute_l10n_bg_code", help="A technical field for tag code"
    )

    def _compute_l10n_bg_code(self):
        for record in self:
            record.l10n_bg_code = "".join(filter(str.isdigit, record.name.upper()))
