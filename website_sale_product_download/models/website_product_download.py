# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class WebsiteProductDownload(models.Model):
    _name = "website.product.download"
    _description = "Website Product Download"
    _order = "id desc"

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        related="product_id.product_tmpl_id", store=True, index=True
    )
    document_id = fields.Many2one(
        "product.document", string="Document", ondelete="set null"
    )
    file_name = fields.Char(required=True)
    user_id = fields.Many2one("res.users", string="User", ondelete="set null")
    partner_id = fields.Many2one(
        "res.partner", string="Customer", ondelete="set null", index=True
    )
    website_id = fields.Many2one("website", ondelete="set null")
    create_date = fields.Datetime(string="Downloaded on", readonly=True)
