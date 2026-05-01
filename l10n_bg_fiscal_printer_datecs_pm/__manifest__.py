# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': 'Datecs PM Fiscal Printer (direct)',
    'summary': """
        Direct Python driver for Datecs PM Communication Protocol v2.11.4
        (FP-700 MX и сродни). Без ErpNet.FP dependency.""",
    'description': """
Direct Python driver за новото поколение Datecs fiscal devices с
PM Communication Protocol v2.11.4. Покрива back-office (фактуриране,
MRP) и POS (retail) сценарии в Odoo 18.

Поддържа три топологии:
* Локален Odoo + serial device
* Cloud Odoo + TCP printer през VPN
* Cloud Odoo + локален Python IoT agent

Паралелен на l10n_bg_erp_net_fp — двата модула съществуват едновременно,
клиентът избира кой да инсталира според своя hardware.
""",
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Point Of Sale',
    'development_status': 'Alpha',
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'base',
        'bus',
        'mail',
        'point_of_sale',
        'account',
    ],
    'external_dependencies': {
        'python': ['pyserial'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/auto_z_cron.xml',
        'views/fiscal_device_views.xml',
        'views/fiscal_receipt_views.xml',
        'views/fiscal_session_views.xml',
        'views/fiscalization_log_views.xml',
        'views/pos_config_views.xml',
        'views/pos_session_views.xml',
        'views/product_template_views.xml',
        'wizard/cash_operation_wizard_views.xml',
        'views/menu_items.xml',
    ],
    'demo': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_bg_fiscal_printer_datecs_pm/static/src/js/datecs_pm_printer.js',
            'l10n_bg_fiscal_printer_datecs_pm/static/src/js/payment_screen.js',
            'l10n_bg_fiscal_printer_datecs_pm/static/src/js/cash_move_popup.js',
            'l10n_bg_fiscal_printer_datecs_pm/static/src/js/opening_control_popup_fiscal.js',
            'l10n_bg_fiscal_printer_datecs_pm/static/src/js/close_pos_popup_patch.js',
            'l10n_bg_fiscal_printer_datecs_pm/static/src/xml/pos_close_popup_template.xml',
        ],
    },
    # 'images': ['static/description/icon.png'],  # add when artwork is ready
    'installable': True,
    'auto_install': False,
    'application': False,
}
