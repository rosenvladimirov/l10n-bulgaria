
# -*- coding: utf-8 -*-
{
    'name': 'HR Version Extension',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Extension for HR Version with work location address and contract amendments',
    'description': """
HR Version Extension
====================
This module extends the HR Version functionality with:
* Work location address field
* Related field for easy access to complete address
* Contract amendments tracking
* Bulgarian labor code compliance fields
* Professional qualifications (NKPD)
* Working time management
* Leave days calculations
    """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'mail',
        'l10n_bg_config',
        'l10n_bg_payroll_classifications',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr.contract.type.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/hr_version_amendment.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_template_view.xml',
        'views/hr_contract_type_views.xml',
        'views/res_company_views.xml',
        'views/hr_job_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}