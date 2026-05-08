"""
product.product extensions — mark fiscal PLUs stale on product change.

When a product's name, list_price or VAT taxes change, any PLU slot
that links to it (M2M) and is currently in `pushed` state gets flipped
to `stale`. The actual re-push happens at the next POS session open;
mid-shift price changes are intentionally NOT auto-pushed (would mix
prices in the same fiscal session and break the audit trail).
"""

from odoo import models


PLU_TRIGGERING_FIELDS = ("name", "list_price", "lst_price", "taxes_id")


class ProductProduct(models.Model):
    _inherit = "product.product"

    def write(self, vals):
        res = super().write(vals)
        if not any(f in vals for f in PLU_TRIGGERING_FIELDS):
            return res
        Plu = self.env["l10n.bg.fiscal.plu"]
        # Find all PLUs that link to any of these products and are in
        # a 'good' state — flip them to stale so the next push picks
        # up the change. Don't touch states that already need attention
        # (conflict / error stay as-is).
        affected = Plu.search(
            [
                ("product_ids", "in", self.ids),
                ("push_state", "in", ("pushed", "pending", "name_drift")),
            ]
        )
        if affected:
            affected.write(
                {
                    "push_state": "stale",
                    "push_message": "Product changed — re-validation required.",
                }
            )
        return res
