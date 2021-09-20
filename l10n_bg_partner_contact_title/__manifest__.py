# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Res Partner Contact title formating',
    'version': '11.0.0.1.0',
    'category': 'hidden',
    'sequence': 30,
    'summary': 'Partner contact title formating',
    'description': """
""",
    'author': 'Rosen Vladimirov, '
              'BioPrint Ltd.',
    'depends': [
        'base',
        'partner_academic_title'
    ],
    'data': [
        'views/res_country_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
