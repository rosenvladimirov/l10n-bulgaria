# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Bg Uic Id Number',
    'summary': """
        Add uid base on partner_identification OCA module""",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/l10n-bulgaria',
    'depends': [
        'l10n_bg',
        'l10n_bg_config',
        'partner_identification',
    ],
    'data': [
    ],
    'demo': [
    ],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
}
