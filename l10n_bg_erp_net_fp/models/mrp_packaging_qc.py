"""
MO + BoM extensions for packaging weight QC.

mrp.bom adds:
    weight_tolerance_percent  — per-BoM tolerance % override
    package_empty_weight      — weight of the empty box/crate (kg)

mrp.production inherits the weighable mixin:
    button "Verify package weight" reads the configured scale, compares
    against `Σ(bom_line.product_id.weight × bom_line.product_qty)` × MO
    quantity / BoM batch quantity, plus the BoM's empty-package weight.
"""

from odoo import _, api, fields, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    weight_tolerance_percent = fields.Float(
        string="Weight tolerance %",
        default=0.0,
        help="Per-BoM override of the company-default packaging "
             "weight tolerance. 0 = use company default. Applied to "
             "MO completion weight verification.",
    )
    package_empty_weight = fields.Float(
        string="Empty package weight (kg)",
        digits=(12, 3),
        default=0.0,
        help="Weight of the empty box / crate / container in which "
             "the BoM output ships. Added to expected total during "
             "weight verification.",
    )


class MrpProduction(models.Model):
    _name = "mrp.production"
    _inherit = ["mrp.production", "l10n.bg.packaging.weighable.mixin"]

    def _packaging_expected_weight(self):
        """Sum BoM line weights × MO quantity scaled vs BoM batch."""
        self.ensure_one()
        if not self.bom_id:
            return sum(
                (line.product_id.weight or 0.0) * line.product_qty
                for line in self.move_raw_ids
            )
        bom = self.bom_id
        # MO quantity is in product_uom_qty; BoM is product_qty for
        # one-batch — scale lines proportionally to the MO size.
        if not bom.product_qty:
            return 0.0
        scale = (self.product_qty or 0.0) / bom.product_qty
        return sum(
            (line.product_id.weight or 0.0) * line.product_qty * scale
            for line in bom.bom_line_ids
        )

    def _packaging_empty_weight(self):
        self.ensure_one()
        if self.bom_id and self.bom_id.package_empty_weight:
            return self.bom_id.package_empty_weight * (
                (self.product_qty or 0.0) / (self.bom_id.product_qty or 1.0)
            )
        return 0.0

    def _packaging_tolerance_percent(self):
        self.ensure_one()
        if self.bom_id and self.bom_id.weight_tolerance_percent:
            return self.bom_id.weight_tolerance_percent
        return super()._packaging_tolerance_percent()
