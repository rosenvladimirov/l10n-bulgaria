{
    'name': 'Bulgaria - Stock Auto Accounting - Manual',
    'summary': """User documentation for the Bulgaria Stock Auto Accounting module, displayed via the Markdown Viewer.""",
    'description': """
Bulgaria - Stock Auto Accounting - Manual
=========================================

Provides an in-app user guide for the **l10n_bg_stock_account** module.

The documentation covers:

* What the module does (auto-post journal entries at picking validation)
* Product category configuration (auto-post flag and the stock accounts)
* The accounting entries generated (302/303/304 <-> 301/GRNI, COGS, scrap, gains)
* Step-by-step usage on receipts and deliveries
* Interaction with l10n_bg_stock_price_diff
* Common mistakes

The guide is displayed inside Odoo through the **markdown_viewer_locale** framework
and is available in Bulgarian and English.
    """,
    'version': '19.0.1.0.0',
    "category": "Accounting/Localizations",
    "development_status": "Beta",
    "license": "LGPL-3",
    'author': 'Rosen Vladimirov, Terraros Commerce Ltd.',
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    'depends': [
        'l10n_bg_stock_account',
        'markdown_viewer_locale',
    ],
    'data': [],
    'assets': {
        'web.assets_backend': [
            ('after', 'markdown_viewer_locale/static/src/js/markdown_registry.js',
             'l10n_bg_stock_account_manual/static/src/js/l10n_bg_stock_account_markdown.js'),
        ],
    },
    'installable': True,
    'application': False,
}
