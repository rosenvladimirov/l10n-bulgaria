# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    "name": "Bulgaria - Commodity Codes (HS6 / CN8 / TARIC10)",
    "summary": "One commodity code per product variant (CN8 or TARIC10), "
               "derived HS6/CN8/TARIC10, yearly CN nomenclature and "
               "helpers for SAF-T, Intrastat and customs.",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "product",
        "account",          # права и меню за счетоводителя (вече идва транзитивно)
        "stock_delivery",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/l10n_bg_cn_code_views.xml",
        "views/product_views.xml",
        "wizards/l10n_bg_cn_code_import_views.xml",
        "wizards/l10n_bg_cn_suggest_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
    "countries": ["BG"],
    "maintainers": ["rosenvladimirov"],
}
