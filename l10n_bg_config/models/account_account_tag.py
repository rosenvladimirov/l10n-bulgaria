#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, fields, models


def get_l10n_bg_applicability():
    return [
        ("declaration", _("Declaration")),
        ("purchase", _("Purchase report")),
        ("sale", _("Sale report")),
        ("vies", _("VIES Report")),
    ]


class AccountAccountTag(models.Model):
    _inherit = "account.account.tag"

    description = fields.Text("Description", translate=True)
    l10n_bg_applicability = fields.Selection(
        selection=get_l10n_bg_applicability(), string="Use for"
    )
    l10n_bg_code = fields.Char(
        "Code", compute="_compute_l10n_bg_code", help="A technical field for tag code"
    )

    def _compute_l10n_bg_code(self):
        for record in self:
            record.l10n_bg_code = "".join(filter(str.isdigit, record.name.upper()))
