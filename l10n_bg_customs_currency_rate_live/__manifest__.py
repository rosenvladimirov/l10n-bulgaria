# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'L10n Bg Customs Currency Rate Live',
    'description': """
        Update currency rate from Customs Agency Bulgaria""",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov',
    'depends': [
        'currency_rate_live',
        'l10n_bg_tax_admin',
    ],
    'data': [
    ],
    'demo': [
    ],
    "post_load": "post_load_hook",
}
