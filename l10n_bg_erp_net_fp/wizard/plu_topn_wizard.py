"""
PLU Top-N best-sellers wizard.

For shops with more active SKUs than device PLU capacity, this wizard
ranks products by sales velocity over a configurable window and:
  - keeps the top-N as `active=True`
  - archives the rest (`active=False`) so they're skipped on push

Sales velocity = sum of pos.order.line qty over the window, per product.
PLUs whose linked products don't appear in the sales report (no recent
sales) get a velocity of 0 and are pushed to the bottom of the ranking.
"""

from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nBgFiscalPluTopNWizard(models.TransientModel):
    _name = "l10n.bg.fiscal.plu.topn.wizard"
    _description = "Activate top-N best-selling PLUs"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    keep_top_n = fields.Integer(
        string="Keep top N",
        required=True,
        default=1500,
        help="Maximum PLU slots to keep active. Tune to your device's "
        "capacity (Datecs DP-150/FP-700X ~2000, Tremol M20 ~5000).",
    )
    window_days = fields.Integer(
        string="Sales window (days)",
        required=True,
        default=90,
        help="Compute sales velocity over this many days back from today.",
    )
    archive_zero_velocity = fields.Boolean(
        string="Archive PLUs with no sales",
        default=True,
        help="If a PLU's linked products have zero sales in the window, "
        "archive it (active=False).",
    )

    def action_compute(self):
        """Dry run — show ranking but don't apply changes."""
        self.ensure_one()
        ranked = self._rank_plus()
        return {
            "type": "ir.actions.act_window",
            "name": _("PLU velocity ranking"),
            "res_model": "l10n.bg.fiscal.plu",
            "view_mode": "list,form",
            "domain": [("id", "in", ranked.ids)],
            "context": {
                "search_default_group_state": 1,
            },
        }

    def action_apply(self):
        self.ensure_one()
        ranked = self._rank_plus()
        if not ranked:
            raise UserError(_("No PLUs to rank."))
        keep = ranked[: self.keep_top_n]
        drop = ranked[self.keep_top_n:]
        keep.write({"active": True})
        if self.archive_zero_velocity and drop:
            drop.write({"active": False})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Top-N applied"),
                "message": _(
                    "Kept active: %(kept)s   Archived: %(dropped)s"
                ) % {"kept": len(keep), "dropped": len(drop)},
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _rank_plus(self):
        """Return PLU recordset ordered by descending sales velocity."""
        self.ensure_one()
        date_from = fields.Datetime.now() - timedelta(days=self.window_days)
        # Aggregate qty per product over the window
        # (skip refunds: positive qty only on the report side)
        self.env.cr.execute(
            """
            SELECT pol.product_id, SUM(pol.qty) AS qty
              FROM pos_order_line pol
              JOIN pos_order po ON po.id = pol.order_id
             WHERE po.company_id = %s
               AND po.date_order >= %s
             GROUP BY pol.product_id
            """,
            (self.company_id.id, date_from),
        )
        velocity_by_product = dict(self.env.cr.fetchall())  # {product_id: qty}

        Plu = self.env["l10n.bg.fiscal.plu"]
        all_plus = Plu.with_context(active_test=False).search(
            [("company_id", "=", self.company_id.id)]
        )

        def plu_velocity(plu):
            return max(
                (velocity_by_product.get(p.id, 0.0) for p in plu.product_ids),
                default=0.0,
            )

        ranked_ids = sorted(
            all_plus.ids,
            key=lambda i: -plu_velocity(all_plus.browse(i)),
        )
        return all_plus.browse(ranked_ids)
