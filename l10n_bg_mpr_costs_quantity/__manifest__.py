# -*- coding: utf-8 -*-
{
    'name': 'Labor Cost by Produced Quantity',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Calculate labor cost based on actual produced quantity',
    'description': '''
        Разпределя разходите за труд пропорционално на
        реално произведеното количество и създава
        автоматични счетоводни записи.
    ''',
    'author': 'Your Company',
    'depends': [
        'mrp',
        'mrp_account',
        'hr',  # За hourly cost на служители
    ],
    'data': [
        'views/res_company_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
