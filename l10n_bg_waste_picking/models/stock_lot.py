# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Stock lot разширение — traceability на отпадъчния произход.

Когато партида рециклиран материал тръгне в производство, искаме да
проследим какво количество от кой код се е консумирало от кой лот в коя
производствена поръчка. Това е база за годишния отчет (Прил. №18).
"""
from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    waste_code_id = fields.Many2one(
        "l10n.bg.waste.code",
        string="Waste Code",
        index=True,
        domain="[('level','=','code')]",
        help="Code under which the material entered the inventory as "
             "waste. Inherited from the source incoming picking.",
    )
    waste_source_picking_ids = fields.Many2many(
        "stock.picking",
        "l10n_bg_waste_lot_picking_rel",
        "lot_id",
        "picking_id",
        string="Source Pickings",
        help="Incoming waste pickings that have contributed to this lot. "
             "When more than one - the lot is mixed; the report 'Origin' "
             "column is filled per quantity ratio.",
    )
    waste_input_kg = fields.Float(
        string="Input Quantity (kg)",
        digits=(16, 3),
        help="Sum of quantities (in kg) booked into this lot from the "
             "source waste pickings.",
    )
    waste_consumed_kg = fields.Float(
        string="Consumed (kg)",
        digits=(16, 3),
        help="Sum of quantities (in kg) consumed from this lot by "
             "downstream manufacturing or outgoing pickings.",
    )

    def name_get(self):
        # Покажи кода в name_get където е uquasable за бърз recall в формите.
        result = []
        for lot in self:
            label = lot.name or ""
            if lot.waste_code_id:
                label = f"{label} [{lot.waste_code_id.code}]"
            result.append((lot.id, label))
        return result
