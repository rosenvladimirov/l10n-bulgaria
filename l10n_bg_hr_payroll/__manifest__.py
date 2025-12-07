# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgarian HR Payroll',
    'version': '19.0.10.0.1',
    'category': 'Human Resources/Payroll/Localization',
    'summary': 'Bulgarian payroll localization with salary rules and labor code compliance',
    'description': """
Bulgarian HR Payroll
====================

This module provides comprehensive Bulgarian payroll functionality for Odoo 18:

Key Features:
-------------
* Complete Bulgarian payroll structure with salary rules
* Social insurance calculations (DOO, ZO, UPF, TZPB)
* Personal income tax (DDFL) at 10% flat rate
* MOD (Minimum Insurance Income) automatic calculations
* Labor Code compliance for employment contracts
* NKPD position integration for qualification mapping
* Economic activity (KID) classification support

Salary Rules & Calculations:
----------------------------
* Basic salary with proration support
* Seniority allowance (minimum 0.6% per year)
* Overtime compensation at 150%
* Comprehensive insurance base aggregation
* Employee and employer social contributions
* Tax calculations with voluntary pension deductions
* Net salary computation

Insurance Contributions (2025 rates):
-------------------------------------
* DOO (State Social Security): 7.8% employee + 12.2% employer
* ZO (Health Insurance): 3.2% employee + 4.8% employer
* UPF (Universal Pension Fund): 2.2% employee + 2.8% employer
* TZPB (Work Accidents): Variable rate based on economic activity

Labor Code Compliance:
----------------------
* Article 66 KT contract requirements validation
* Minimum annual leave (20 working days)
* Notice period validation (30-90 days for indefinite contracts)
* Probation period limits (max 6 months)
* Working hours compliance (8h/day, 40h/week for full-time)
* MOD wage floor enforcement

Technical Implementation:
-------------------------
* Python-based salary rule calculations
* Rule parameters for easy rate updates
* Configurable insurance base code lists
* Integration with hr_contract extended fields
* Real-time compliance validation
* Comprehensive payslip structure

This module ensures full compliance with Bulgarian labor and tax regulations
while providing flexible payroll processing capabilities.
        """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria-ее',
    'license': 'OPL-1',
    'depends': [
        'base',
        'hr',
        'hr_holidays',
        'hr_payroll',
        'hr_work_entry',
        'l10n_bg_hr',
        'hr_work_entry_holidays_enterprise',
        'l10n_bg_payroll_classifications',
        'l10n_bg_hr_holidays',
        'l10n_bg_config',
        'l10n_bg_city',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_structure_type.xml',
        'data/hr_payroll_structure.xml',
        'data/hr_salary_rule_category.xml',
        'data/rule_parameters.xml',
        'data/hr_salary_rule.xml',
        'data/hr_payroll_structure_inputs.xml',
        'views/hr_employee_views.xml',
        'views/hr_version_views.xml',
        'views/hr_version_nssi.xml',
        'views/bg_ncop_classification.xml',
        'views/l10n_bg_nap_export_history.xml',
        'views/hr_work_entry_type_views.xml',
        'views/hr_payslip_views.xml',
        'views/l10n_bg_nssi_leave_reason.xml',
        'views/hr_version_amendment.xml',
        'views/hr_menus.xml'
    ],
    'demo': [],
    'assets': {},
    'images': [
        'static/description/banner.png',
        # 'static/description/icon.png',
    ],
    'external_dependencies': {
        'python': [],
        'bin': [],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'bootstrap': False,
    'maintainers': ['rosenvladimirov'],
    'contributors': ['Rosen Vladimirov'],
    'support': 'https://github.com/rosenvladimirov/l10n-bulgaria/issues',
    'countries': ['BG'],
    "price": 250,
    "price_currency": "EUR",
}
