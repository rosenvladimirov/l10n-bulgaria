# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "eCommerce Product Page Translation",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "category": "Website/Website",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "summary": "Translate every element of the eCommerce product page from the "
    "backend, term by term, in one wizard.",
    "depends": ["website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/product_page_translate_wizard_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
}
