# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Bg Report Stock",
    "summary": """Bulgaria - Accepted delivery documents in stock picking""",
    "version": "19.0.1.1.7",
    # OCA Metadata
    "development_status": 'Beta',
    "license": "AGPL-3",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "stock",
        "l10n_bg_report_theme"
    ],
    "data": [
        "report/report_accepted_deliveryslip.xml",
        "report/stock_report_views.xml",
        "views/stock_picking_views.xml"
    ],
    "demo": [],
    'images': [
        'static/description/banner.png',
    ],

    'tags': ['localization', 'stock', 'bulgaria', 'reports'],

    # Version requirements
    'odoo_version': '19.0',
    'python_version': '>=3.11',
}
