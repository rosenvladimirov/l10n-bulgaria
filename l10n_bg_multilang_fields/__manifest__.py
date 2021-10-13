# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Res Partner lang fields',
    'version': '11.0.0.1.0',
    'category': 'hidden',
    'sequence': 30,
    'summary': 'Multilang fields in res partner form',
    'description': """
""",
    'author': 'Dr. Stamatios Priftis, '
              'Rosen Vladimirov',
    'depends': [
        'base',
        'l10n_bg_multilang'
    ],
    'data': [
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}