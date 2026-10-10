# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_bg_sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Quotation",
        copy=False,
        index="btree_not_null",
        help="Quotation saved from the wholesale form of the Point of Sale.",
    )

    @api.model
    def _l10n_bg_b2b_unpack_form(self, order):
        # Връзката към офертата идва в същия JSON (ADR 0003): само SO на
        # същия клиент, иначе се изпуска.
        super()._l10n_bg_b2b_unpack_form(order)
        form = order.get("l10n_bg_b2b_form")
        if not isinstance(form, dict):
            return
        sale_order_id = form.get("sale_order_id")
        if not isinstance(sale_order_id, int) or not order.get("partner_id"):
            return
        partner = self.env["res.partner"].browse(order["partner_id"]).exists()
        if partner and self.env["sale.order"].search_count([
            ("id", "=", sale_order_id),
            ("partner_id.commercial_partner_id", "=", partner.commercial_partner_id.id),
        ]):
            order["l10n_bg_sale_order_id"] = sale_order_id
