# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_download = fields.Boolean(
        string="Free Download",
        help="Show a Download button on the product page instead of Add to Cart. "
        "It downloads the document of the selected variant that is visible on "
        "confirmed orders. Only for products with a zero sales price.",
    )
    website_download_count = fields.Integer(
        string="Downloads",
        compute="_compute_website_download_count",
    )

    def _compute_website_download_count(self):
        counts = dict(
            self.env["website.product.download"]._read_group(
                [("product_tmpl_id", "in", self.ids)],
                ["product_tmpl_id"],
                ["__count"],
            )
        )
        for template in self:
            template.website_download_count = counts.get(template, 0)

    @api.constrains("website_download", "list_price")
    def _check_website_download_free(self):
        # Безплатното сваляне е само за безплатни продукти: иначе бутонът
        # би раздавал файлове, които се продават
        for template in self:
            if template.website_download and template.list_price:
                raise ValidationError(
                    _(
                        "The product %s has a sales price: only free products "
                        "can be downloaded from the website.",
                        template.display_name,
                    )
                )

    def _get_website_download_document(self, product):
        """Документът за сваляне на варианта: първо на варианта, после на шаблона."""
        self.ensure_one()
        documents = (product.product_document_ids | self.product_document_ids).filtered(
            lambda doc: doc.active and doc.attached_on_sale == "sale_order"
        )
        return documents.sorted(
            lambda doc: (doc.res_model != "product.product", doc.sequence, doc.id)
        )[:1]

    def action_view_website_downloads(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "website_sale_product_download.action_website_product_download"
        )
        action["domain"] = [("product_tmpl_id", "=", self.id)]
        action["context"] = {"default_product_tmpl_id": self.id}
        return action
