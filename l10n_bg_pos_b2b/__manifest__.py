# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Bulgaria - Wholesale (B2B) sales in the Point of Sale",
    "summary": "Wholesale mode in the POS: business customers are always "
    "invoiced, invoice data and credit are checked before payment",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "license": "LGPL-3",
    "countries": ["BG"],
    # Без зависимост от фискално устройство: лепилото към ErpNet.FP е
    # l10n_bg_erp_net_fp_pos_b2b (котвата specs/pos-b2b-wholesale §3).
    "depends": ["point_of_sale", "l10n_bg_config", "l10n_bg_pos_sales_report"],
    "data": [
        "security/l10n_bg_pos_b2b_security.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_bg_pos_b2b/static/src/app/**/*",
        ],
        "web.assets_tests": [
            "l10n_bg_pos_b2b/static/tests/tours/**/*",
        ],
    },
    "installable": True,
}
