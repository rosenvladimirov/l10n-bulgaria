# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    'name': 'ErpNet.FP Fleet — Zebra / Symbol Scanners Plugin',
    'summary': "Zebra/Symbol barcode readers (DS2208, DS3678, LS2208) catalog + auto YAML push.",
    'version': '19.0.1.0.0',
    'author': 'Rosen Vladimirov',
    'license': 'LGPL-3',
    'category': 'Fleet',
    'depends': ['l10n_bg_erp_net_fp_fleet'],
    'data': [
        'security/ir.model.access.csv',
        'views/zebra_reader_views.xml',
        'views/zebra_reader_template_views.xml',
        'data/zebra_reader_templates.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
