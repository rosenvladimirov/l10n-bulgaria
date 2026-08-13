{
    'name': 'Inventory - Manual (Bulgaria)',
    'summary': """Bulgarian-oriented user guide for the Inventory app, displayed via the Markdown Viewer.""",
    'description': """
Inventory - Manual (Bulgaria)
================================

Provides an in-app user guide for the **stock** app, focused on the
Bulgarian localization documents actually generated on top of it: the
handover protocol and accepted-delivery slip added by `l10n_bg_report_stock`,
the sale-order line description shown on delivery slips
(`l10n_bg_stock_sale_line_description`), and practical guidance on
multi-warehouse setups.

The guide is displayed inside Odoo through the **markdown_viewer_locale**
framework and is available in Bulgarian and English.
    """,
    'version': '18.0.1.0.0',
    "category": "Inventory/Inventory",
    "development_status": "Beta",
    "license": "OPL-1",
    'author': 'Rosen Vladimirov',
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    'depends': ['stock', 'markdown_viewer_locale'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            ('after', 'markdown_viewer_locale/static/src/js/markdown_registry.js',
             'inventory_manual/static/src/js/inventory_markdown.js'),
        ],
    },
    "price": 0,
    "price_currency": "EUR",
    "installable": True,
    "application": False,
}
