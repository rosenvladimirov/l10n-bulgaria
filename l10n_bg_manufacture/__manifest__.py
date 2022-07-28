# Copyright 2022 Rosen Vladimirov, BioPrint Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Bg Manufacture',
    'summary': """
        Add account move for transit 601 account in manufacture.""",
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov, BioPrint Ltd.,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'depends': [
        'l10n_bg',
        'mrp',
        'stock_account',
    ],
    'data': [
        'views/stock_account_views.xml',
    ],
    'demo': [
    ],
}
