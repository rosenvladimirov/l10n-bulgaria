# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    'name': 'ErpNet.FP Fleet — CAS Scales Plugin',
    'summary': "CAS weighing scales (PR-Plus, CL-5000, bench) catalog + auto YAML push.",
    'version': '19.0.1.0.1',
    'author': 'Rosen Vladimirov',
    'license': 'LGPL-3',
    'category': 'Fleet',
    'depends': ['l10n_bg_erp_net_fp_fleet'],
    'data': [
        'security/ir.model.access.csv',
        'views/cas_scale_views.xml',
        'views/cas_scale_template_views.xml',
        'data/cas_scale_templates.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
