# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Bulgaria - Wholesale (B2B) in the Point of Sale with sale orders",
    "summary": "Wholesale sales in the POS saved as quotations: sale order "
    "number, quotation and pro-forma printed in the POS",
    "version": "19.0.1.1.3",
    "category": "Sales/Point of Sale",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "license": "LGPL-3",
    "countries": ["BG"],
    # Лепило: основният B2B модул остава без зависимост от Продажби
    # (ADR specs/pos-b2b-wholesale/0003).
    "depends": ["l10n_bg_pos_b2b", "pos_sale"],
    "auto_install": True,
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_bg_pos_b2b_sale/static/src/app/**/*",
        ],
        "web.assets_tests": [
            "l10n_bg_pos_b2b_sale/static/tests/tours/**/*",
        ],
    },
    "installable": True,
}
