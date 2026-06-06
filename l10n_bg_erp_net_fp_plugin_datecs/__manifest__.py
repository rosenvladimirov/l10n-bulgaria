# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    'name': 'ErpNet.FP Fleet — Datecs Plugin',
    'summary': """
        Datecs hardware catalog: fiscal printers (DP-150 / FP-700MX /
        BlueCash 50-55) + pinpads (BluePad-55). Auto-generates YAML
        fragments pushed to the proxy.""",
    'description': """
Datecs hardware plug-in за ErpNet.FP Fleet. Каталог + Apply Template
workflow подобно на Polimex plug-in-а:

- datecs.printer — fiscal printer record (DP-150, FP-700MX, BlueCash)
- datecs.printer.template — catalog с pre-seeded модели
- datecs.pinpad — pinpad terminal record (BluePad-55)
- datecs.pinpad.template — catalog
- Apply Template action — auto-creates parts/properties от template
- get_config_payload() — генерира YAML fragments за proxy push_config

Pre-seeded models:
- Datecs DP-150 (entry-level fiscal printer, serial)
- Datecs FP-700MX (PLU-only fiscal printer)
- Datecs BlueCash-50 (mobile fiscal + scanner)
- Datecs BlueCash-55 (mobile fiscal + pinpad + scanner)
- Datecs BluePad-55 (BLE pinpad)
    """,
    'version': '20.0.1.4.0',
    'author': 'Rosen Vladimirov',
    'license': 'LGPL-3',
    'category': 'Fleet',
    'depends': [
        'l10n_bg_erp_net_fp_fleet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/datecs_printer_views.xml',
        'views/datecs_printer_template_views.xml',
        'views/datecs_pinpad_views.xml',
        'views/datecs_pinpad_template_views.xml',
        'data/datecs_printer_templates.xml',
        'data/datecs_pinpad_templates.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
