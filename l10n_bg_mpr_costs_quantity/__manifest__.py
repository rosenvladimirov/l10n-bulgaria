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
        'mrp_workorder',
        'hr',  # За hourly cost на служители
    ],
    'data': [
        'views/mrp_workcenter_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
