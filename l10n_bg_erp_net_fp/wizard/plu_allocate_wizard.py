"""
PLU allocation wizard — pick a set of `product.product` records and
add them to the PLU base. Each picked product is allocated the next
free PLU number; one PLU slot per product (M2M can be edited later).
Existing PLU links are skipped (no duplicates).
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nBgFiscalPluAllocateWizard(models.TransientModel):
    _name = "l10n.bg.fiscal.plu.allocate.wizard"
    _description = "Allocate fiscal PLUs for selected products"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    source_pricelist_id = fields.Many2one(
        "product.pricelist",
        required=True,
        default=lambda self: self.env["l10n.bg.fiscal.plu"]._default_source_pricelist(),
    )
    product_ids = fields.Many2many(
        "product.product",
        string="Products to allocate",
        required=True,
    )
    skip_existing = fields.Boolean(
        default=True,
        help="If True, products already linked to a PLU slot are skipped silently. "
        "If False, they raise an error.",
    )
    department_id = fields.Integer(default=1)
    auto_validate = fields.Boolean(
        default=True,
        help="Run consistency check on each created PLU immediately.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids")
        active_model = self.env.context.get("active_model")
        if active_model == "product.product" and active_ids:
            res["product_ids"] = [(6, 0, active_ids)]
        elif active_model == "product.template" and active_ids:
            templates = self.env["product.template"].browse(active_ids)
            res["product_ids"] = [
                (6, 0, templates.product_variant_ids.ids)
            ]
        return res

    def action_allocate(self):
        self.ensure_one()
        Plu = self.env["l10n.bg.fiscal.plu"]
        # Find products already linked to a PLU in this company
        existing = Plu.search(
            [
                ("company_id", "=", self.company_id.id),
                ("product_ids", "in", self.product_ids.ids),
            ]
        )
        existing_products = existing.mapped("product_ids")
        to_allocate = self.product_ids - existing_products

        if not to_allocate:
            raise UserError(
                _("All selected products are already linked to PLU slots.")
            )

        if existing_products and not self.skip_existing:
            names = ", ".join(existing_products.mapped("display_name"))
            raise UserError(
                _("These products are already linked to PLU slots: %s") % names
            )

        created = self.env["l10n.bg.fiscal.plu"]
        for product in to_allocate:
            # `create` will auto-allocate plu_number via _next_free_plu
            try:
                expected_price = self.source_pricelist_id._get_product_price(
                    product, quantity=1.0
                )
            except Exception:
                expected_price = product.list_price
            plu = Plu.create(
                {
                    "company_id": self.company_id.id,
                    "source_pricelist_id": self.source_pricelist_id.id,
                    "product_ids": [(6, 0, [product.id])],
                    "name": product.display_name,
                    "price": expected_price,
                    "department_id": self.department_id,
                }
            )
            if self.auto_validate:
                plu._check_consistency()
            created |= plu

        return {
            "type": "ir.actions.act_window",
            "name": _("Allocated PLU slots"),
            "res_model": "l10n.bg.fiscal.plu",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }
