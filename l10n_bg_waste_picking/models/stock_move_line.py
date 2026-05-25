# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Stock move line: waste_code_id + auto-converted kg + произход.

Odoo 19: stock.move.line полето за реално движено количество е `quantity`
(не `qty_done` — то беше deprecated в 18). Конверсията към kg минава
през ml.product_uom_id._compute_quantity().
"""
from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    waste_code_id = fields.Many2one(
        "l10n.bg.waste.code",
        string="Waste Code",
        index=True,
        domain="[('level','=','code')]",
    )
    waste_quantity_kg = fields.Float(
        string="Quantity (kg)",
        digits=(16, 3),
        compute="_compute_waste_quantity_kg",
        store=True,
        index=True,
    )
    waste_origin_partner_id = fields.Many2one(
        "res.partner",
        string="Origin (Legal Entity)",
        compute="_compute_waste_origin",
        store=True,
        help="The legal entity that handed over this waste (sender of the "
             "incoming picking). Used by the Annex 4 'Sender' column.",
    )

    @api.depends("quantity", "product_uom_id", "product_id.is_waste_product")
    def _compute_waste_quantity_kg(self):
        uom_kg = self.env.ref("uom.product_uom_kgm", raise_if_not_found=False)
        for ml in self:
            if not ml.product_id.is_waste_product or not uom_kg:
                ml.waste_quantity_kg = 0.0
                continue
            if not ml.product_uom_id or not ml.quantity:
                ml.waste_quantity_kg = 0.0
                continue
            ml.waste_quantity_kg = ml.product_uom_id._compute_quantity(
                ml.quantity, uom_kg
            )

    @api.depends("picking_id.partner_id")
    def _compute_waste_origin(self):
        # В incoming picking-и: партньорът на пикета е изпращачът.
        for ml in self:
            ml.waste_origin_partner_id = ml.picking_id.partner_id
