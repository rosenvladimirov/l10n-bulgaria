# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    'name': 'Bulgarian HR: Employment Contract (Labour Code)',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Contracts',
    'summary': 'Bulgarian Labour Code data on the employment contract, '
               'contract amendments, TELK decisions and document expiry',
    'description': """
Bulgarian HR: Employment Contract
=================================
The Labour Code layer of the Bulgarian HR localization, without payroll:

* Art. 66 LC contract terms on the employment contract (number, dates,
  NKPD position, economic activity, leave, notice, working time)
* Bulgarian contract types (codes 001-021) and their duration under Art. 68 LC
* Contract amendments (Art. 119 LC): snapshot of the previous terms,
  activation on the effective date, temporary assignment under Art. 120 LC
  and automatic return on expiry
* Fixed-term contracts: agreed end of the term, warning before it and a
  marker after the Art. 69 LC window
* TELK/NELK decisions with their validity period
* Personal documents (ID card, protection status) and their expiry
  notification, personal doctor, foreign tax number
    """,
    'author': 'Rosen Vladimirov, Terraros Commerce Ltd.',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'license': 'LGPL-3',
    'depends': [
        'hr_contract',
        'mail',
        'l10n_bg_config',
        'l10n_bg_payroll_classifications',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/hr.contract.type.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/hr_contract_amendment.xml',
        'views/hr_contract_views.xml',
        'views/hr_contract_type_views.xml',
        'views/l10n_bg_telk_decision_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_job_views.xml',
        'views/res_company_views.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'countries': ['BG'],
}
