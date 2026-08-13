{
    'name': 'Purchase - Manual (Bulgaria)',
    'summary': """Bulgarian-oriented user guide for the Purchase app, displayed via the Markdown Viewer.""",
    'description': """
Purchase - Manual (Bulgaria)
==============================

Provides an in-app user guide for the **purchase** app. Important note
reflected throughout this guide: no Bulgarian localization module changes
`purchase.order` itself — all VAT/protocol/customs logic (Art. 82(2) reverse
charge, EU intra-community acquisition, import from third countries) lives
on the **vendor bill** created from the purchase order, handled by
`l10n_bg_tax_admin`. This guide bridges the standard purchasing workflow
with that accounting-side logic so buyers know what to expect once a bill
is generated.

The guide is displayed inside Odoo through the **markdown_viewer_locale**
framework and is available in Bulgarian and English.
    """,
    'version': '18.0.1.0.0',
    "category": "Inventory/Purchase",
    "development_status": "Beta",
    "license": "OPL-1",
    'author': 'Rosen Vladimirov',
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    'depends': ['purchase', 'markdown_viewer_locale'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            ('after', 'markdown_viewer_locale/static/src/js/markdown_registry.js',
             'purchase_manual/static/src/js/purchase_markdown.js'),
        ],
    },
    "price": 0,
    "price_currency": "EUR",
    "installable": True,
    "application": False,
}
