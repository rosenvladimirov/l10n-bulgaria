#  Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgarian HR Payroll Classifications',
    'version': '18.0.6.0.1',
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

    NCOP Classifications:
    ---------------------
    * Complete NCOP hierarchy management (НКПД 2011)
    * Professional groups and categories
    * Integration with employee positions

    Economic Activities (KID):
    --------------------------
    * Full KID classification structure (Sections, Divisions, Groups, Classes)
    * MOD (Minimum Insurance Income) rates by qualification groups
    * Hierarchical structure with parent-child relationships

    This module is essential for Bulgarian companies to comply with local labor regulations
    and properly classify employees according to Bulgarian standards.
        """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        # КИД structure is now defined canonically in l10n_bg_config
        # (model l10n.bg.kid); this module prototype-inherits it.
        'l10n_bg_config',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/bg_hr_payroll_economic_activity/parent/bg.hr.payroll.economic.activity.csv',
        'data/bg_hr_payroll_economic_activity/div/bg.hr.payroll.economic.activity.csv',
        'data/bg_hr_payroll_economic_activity/grp/bg.hr.payroll.economic.activity.csv',
        'data/bg_hr_payroll_economic_activity/cls/bg.hr.payroll.economic.activity.csv',
        'data/bg_hr_payroll_ncop_classification/major/bg.hr.payroll.ncop.classification.csv',
        'data/bg_hr_payroll_ncop_classification/sub_major/bg.hr.payroll.ncop.classification.csv',
        'data/bg_hr_payroll_ncop_classification/minor/bg.hr.payroll.ncop.classification.csv',
        'data/bg_hr_payroll_ncop_classification/unit/bg.hr.payroll.ncop.classification.csv',
        'data/bg_hr_payroll_ncop_classification/occupation/bg.hr.payroll.ncop.classification.csv',
        'views/bg_ncop_classification.xml',
        'views/bg_mod_economic_activity.xml',
        'views/hr_job_views.xml',
        'views/hr_menus.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'maintainers': ['rosenvladimirov'],
    'contributors': ['Rosen Vladimirov'],
    'support': 'https://github.com/rosenvladimirov/l10n-bulgaria/issues',
    'countries': ['BG'],
}
