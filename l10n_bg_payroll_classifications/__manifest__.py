#  Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgarian HR Payroll Classifications',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Localization',
    'summary': 'Bulgarian localization for HR payroll with NKPD and Economic Activity classifications',
    'description': """
    Bulgarian HR Payroll Classifications
    ====================================

    This module provides Bulgarian localization for HR and payroll management with:

    Key Features:
    -------------
    * NCOP (National Classification of Occupations and Positions) management
    * Economic Activities (KID) classification with MOD rates
    * Bulgarian-specific HR menus structure
    * Integration with standard HR modules
    * Support for TZPB (Work Accident Insurance) rates per activity

    NCOP Classifications:
    --------------------
    * Complete NCOP hierarchy management (НКПД 2011)
    * Professional groups and categories
    * Integration with employee positions

    Economic Activities (KID):
    -------------------------
    * Full KID classification structure (Sections, Divisions, Groups, Classes)
    * MOD (Minimum Insurance Income) rates by qualification groups
    * TZPB rates per economic activity
    * Hierarchical structure with parent-child relationships

    This module is essential for Bulgarian companies to comply with local labor regulations
    and properly classify employees according to Bulgarian standards.
        """,
    'author': 'Your Company',
    'website': 'https://github.com/your-company',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_contract',
    ],
    'external_dependencies': {
        'python': [],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/bg_nkpd_classifications.csv',
        'data/bg_mod_economic_activities.csv',
        'views/hr_menus.xml',
        'views/bg_nkpd_classification.xml',
        'views/bg_mod_economic_activity.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
