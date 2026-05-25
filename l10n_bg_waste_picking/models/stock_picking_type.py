# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Stock picking type — добавя default R/D дейност за waste-related types.

Така входящите picking-и от тип 'Receipt' могат да са pre-set към R3 за
Полигруп (рециклиране), R13 (съхраняване) или каквото е приложимо.
"""
from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    waste_default_activity_id = fields.Many2one(
        "l10n.bg.waste.activity",
        string="Default Waste Activity",
        help="The R/D activity preset on new pickings of this type. "
             "Typically R3 for plastic recycling intake, R13 for storage.",
    )
    is_waste_intake = fields.Boolean(
        string="Waste Intake",
        help="When set, this picking type is for accepting incoming waste. "
             "The validation flow always opens the waste code wizard if "
             "any move line targets a product flagged as waste.",
    )
