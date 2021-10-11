# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Bulgaria - Base address extended",
    "version": "11.0.4.0",
    "author": "Rosen Vladimirov, "
              "BioPrint Ltd.",
    'category': 'Localization',
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "description": """
    """,
    'depends': [
        'base',
        'base_address_city',
        'base_address_extended',
        'contacts',
    ],
    "demo": [],
    "data": [
        'security/ir.model.access.csv',
        'views/res_city_views.xml',
        'views/base_address_extended.xml',
    ],
    "license": "AGPL-3",
    "installable": True,
}
