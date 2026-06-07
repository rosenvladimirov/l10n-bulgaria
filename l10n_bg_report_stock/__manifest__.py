# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Bg Report Stock",
    "summary": """Bulgaria - Accepted delivery documents in stock picking""",
    "version": "20.0.1.0.0",
    # OCA Metadata
    "development_status": 'Beta',
    "license": "AGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "stock",
        "l10n_bg_report_theme"
    ],
    "data": [
        "report/report_accepted_deliveryslip.xml",
        "report/stock_report_views.xml"
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
