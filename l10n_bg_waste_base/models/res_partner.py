# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""res.partner разширение: флаг за оператор на отпадъци + връзка към разрешителни.

Разрешителните се дефинират в `l10n_bg_waste_permit`; полето тук е placeholder
с computed visibility — модулът `_base` не разчита на тяхното съществуване.
"""
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_waste_operator = fields.Boolean(
        string="Waste Operator",
        help="The partner holds a Bulgarian waste treatment permit "
             "(Art. 35/67/78 of the Waste Management Act). Set when this "
             "partner can legally act as sender, carrier or receiver in "
             "waste pickings.",
    )
    waste_operator_role_ids = fields.Many2many(
        "l10n.bg.waste.activity",
        "l10n_bg_waste_partner_activity_rel",
        "partner_id",
        "activity_id",
        string="Permitted Activities",
        help="R/D activities that this partner is authorised to perform. "
             "Used as a hint when picking a counterpart on a waste picking.",
    )
