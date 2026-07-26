{
    'name': 'Sales - Manual (Bulgaria)',
    'summary': """Bulgarian-oriented user guide for the Sales app, displayed via the Markdown Viewer.""",
    'description': """
Sales - Manual (Bulgaria)
==========================

Provides an in-app user guide for the **sale** app, focused on the Bulgarian
localization features actually used on top of it: the accepted-delivery /
handover protocol report, the sale-order line description on delivery slips,
awareness of how the customer's country/VAT determine invoicing treatment,
and the NRA e-shop alternative-regime reporting.

The guide is displayed inside Odoo through the **markdown_viewer_locale**
framework and is available in Bulgarian and English.
    """,
    'version': '19.0.1.0.0',
    "category": "Sales/Sales",
    "development_status": "Beta",
    "license": "OPL-1",
    'author': 'Rosen Vladimirov',
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    'depends': ['sale', 'markdown_viewer_locale'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            ('after', 'markdown_viewer_locale/static/src/js/markdown_registry.js',
             'sale_manual/static/src/js/sale_markdown.js'),
        ],
    },
    "price": 0,
    "price_currency": "EUR",
    "installable": True,
    "application": False,
}
