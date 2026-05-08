"""
product.pricelist + product.pricelist.item extensions — mark fiscal
PLUs stale when pricelist rules change.

Any pricelist write (item add/remove/edit) that affects a pricelist
used as a PLU `source_pricelist_id` flips the affected PLUs to stale.
"""

from odoo import models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def write(self, vals):
        res = super().write(vals)
        if "item_ids" in vals or "currency_id" in vals:
            self._mark_plu_stale()
        return res

    def _mark_plu_stale(self):
        Plu = self.env["l10n.bg.fiscal.plu"]
        affected = Plu.search(
            [
                ("source_pricelist_id", "in", self.ids),
                ("push_state", "in", ("pushed", "pending", "name_drift")),
            ]
        )
        if affected:
            affected.write(
                {
                    "push_state": "stale",
                    "push_message": "Source pricelist changed — re-validation required.",
                }
            )


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def write(self, vals):
        res = super().write(vals)
        self.mapped("pricelist_id")._mark_plu_stale()
        return res

    def unlink(self):
        pricelists = self.mapped("pricelist_id")
        res = super().unlink()
        pricelists._mark_plu_stale()
        return res
