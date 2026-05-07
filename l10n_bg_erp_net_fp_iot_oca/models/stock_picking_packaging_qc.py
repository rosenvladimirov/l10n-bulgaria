"""
stock.picking extension for packaging weight QC.

Same flow as mrp.production but expected weight comes from move lines
(typically `move_ids_without_package` or the done quantities). Empty
package weight comes from the company default since pickings don't
have a single BoM.
"""

from odoo import _, api, fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.bg.packaging.weighable.mixin"]

    def _packaging_expected_weight(self):
        """Sum (product.weight × done_quantity) over move lines."""
        self.ensure_one()
        total = 0.0
        for move in self.move_ids:
            qty = move.quantity if move.state != "draft" else move.product_uom_qty
            total += (move.product_id.weight or 0.0) * (qty or 0.0)
        return total

    def _packaging_empty_weight(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        return getattr(
            company, "default_packaging_empty_weight", 0.0
        ) or 0.0
