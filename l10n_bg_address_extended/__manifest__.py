# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Bulgaria - Base address extended",
    "version": "19.0.1.0.1",
    "author": "Rosen Vladimirov",
    "category": "Localization",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "description": """
    Perfect for organizations requiring precise Bulgarian address formatting and management within their Odoo implementation.
    """,
    "depends": [
        "base",
        "base_address_extended",
    ],
    "demo": [],
    "data": [
        "views/base_address_extended.xml",
    ],
    "license": "AGPL-3",
    'images': [
        'static/description/banner.png',
    ],
    'tags': ['localization', 'bulgaria', 'configuration'],

    # Version requirements
    'odoo_version': '19.0',
    'python_version': '>=3.11',
}
