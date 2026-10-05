# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Bulgaria - eShop invoice request and monthly sales report",
    "summary": "'I want an invoice' on checkout; orders without it are invoiced "
    "monthly to the random customer as a sales report (document type 81)",
    "version": "19.0.2.1.0",
    "category": "Website/Website",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "license": "LGPL-3",
    "countries": ["BG"],
    "depends": ["website_sale", "l10n_bg_ledger", "l10n_bg_config"],
    "data": [
        "data/ir_cron.xml",
        "views/sale_order_views.xml",
        "views/templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_bg_website_sale_invoice_request/static/src/interactions/**/*",
        ],
    },
    "installable": True,
}
