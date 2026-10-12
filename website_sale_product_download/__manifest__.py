# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "eCommerce: Free Product Download",
    "summary": "Download button on the product page for free software, per variant",
    "description": """
Free downloads in the shop, the way the Odoo Apps store works.

A product marked as Free Download shows a Download button instead of
Add to Cart. The button downloads the file of the selected variant
(for example Windows or Linux): the product documents visible on
confirmed orders. The visitor signs in first; every download is logged
with the customer and counted on the product.
""",
    "version": "19.0.1.0.0",
    "category": "Website/Website",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "website_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/website_product_download_views.xml",
        "views/templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
