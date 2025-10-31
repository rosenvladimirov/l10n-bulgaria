{
    'name': 'Bulgaria - HR Holidays',
    'version': '18.0.1.0.2',
    'category': 'Human Resources/Time Off',
    'summary': 'Bulgarian localization for HR Holidays',
    'description': """
Bulgarian Leave Types for Odoo
===============================

This module adds all official leave types for Bulgaria, including:

* 17 NHIF (NZOK) sick leave types (codes 01-17)
* 4 Annual paid leave types (Art. 155-157 Labor Code)
* 8 Civil and public duty leave types (Art. 157 Labor Code)
* 4 Special leave types (Art. 158-161 Labor Code)
* 7 Maternity and paternity leave types (Art. 163-168 Labor Code)
* 4 Educational leave types (Art. 169-171a Labor Code)

Total: 61 leave types

All leave types are compliant with:
* Bulgarian Labor Code (Кодекс на труда)
* NHIF Standards (НЗОК стандарти)
* Regulation on Working Time, Rest and Leave (НРВПО)

Features:
---------
* Pre-configured leave types with appropriate settings
* Color-coded for easy identification
* Proper document requirements
* Correct allocation and validation settings
* Bulgarian Labor Code references
* Bilingual naming (Bulgarian/English)

Installation:
-------------
1. Install the module through Odoo Apps
2. Go to HR > Configuration > Time Off Types to view all leave types
3. Configure allocations for annual leave types
4. Set responsible persons for approval workflows

Configuration:
--------------
After installation:
1. Review and adjust leave types if needed
2. Create allocations for employees (for annual leave)
3. Configure approval workflows
4. Set email notifications

Support:
--------
For questions about Bulgarian labor legislation, consult with:
* HR specialist
* Accountant
* Labor lawyer

Documentation:
--------------
Full documentation available in the module's data folder:
* hr_leave_types_documentation_bg.md - Detailed documentation
* quick_reference_bg.md - Quick reference guide
* README.md - Installation and usage guide
    """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'license': 'LGPL-3',
    'depends': [
        'hr_contract',
        'hr_holidays',
        'l10n_bg',
    ],
    'data': [
        'data/nssi.leave.reason.csv',
        'data/hr_holidays_data.xml',
        'security/ir.model.access.csv',
        'views/hr_leave_views.xml',
        'views/hr_leave_type_views.xml',
        'views/l10n_bg_nssi_leave_reason.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'maintainers': ['rosenvladimirov'],
    'contributors': ['Rosen Vladimirov'],
    'support': 'https://github.com/rosenvladimirov/l10n-bulgaria/issues',
    'countries': ['BG'],
}
