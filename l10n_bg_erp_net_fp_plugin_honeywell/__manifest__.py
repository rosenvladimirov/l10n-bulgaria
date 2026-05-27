# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    'name': 'ErpNet.FP Fleet — Honeywell Scanners Plugin',
    'summary': "Honeywell barcode readers (1470g, 1250g, 5145) catalog + auto YAML push.",
    'version': '18.0.1.1.0',
    'author': 'Rosen Vladimirov',
    'license': 'LGPL-3',
    'category': 'Fleet',
    'depends': ['l10n_bg_erp_net_fp_fleet'],
    'data': [
        'security/ir.model.access.csv',
        'views/honeywell_reader_views.xml',
        'views/honeywell_reader_template_views.xml',
        'data/honeywell_reader_templates.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
