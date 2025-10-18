{
    'name': 'Bulgaria - HR Holidays',
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Bulgarian localization for HR Holidays',
    'description': """
Bulgarian Localization for HR Holidays
=======================================

This module adds:
    * Bulgarian leave types according to Bulgarian Labor Code
    * Configuration for paid annual leave (20 working days minimum)
    * Sick leave types
    * Unpaid leave
    * Maternity/Paternity leave
    * Study leave
    * Other leave types according to Bulgarian legislation
    """,
    'author': 'Your Company',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'license': 'LGPL-3',
    'depends': [
        'hr_holidays',
        'l10n_bg',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        # 'data/hr_leave_type_data.xml',
        # 'views/hr_leave_views.xml',
    ],
    'demo': [
        # 'demo/hr_leave_demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'maintainers': ['rosenvladimirov'],
    'contributors': ['Rosen Vladimirov'],
    'support': 'https://github.com/rosenvladimirov/l10n-bulgaria/issues',
    'countries': ['BG'],
}
