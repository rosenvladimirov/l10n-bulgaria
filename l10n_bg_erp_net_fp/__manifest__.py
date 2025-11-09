
# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': 'ErpNet.FP Fiscal Printer for odoo',
    'summary': """
        Integration with ERP.BG fiscal printers through ErpNet.FP server.
        Supports real-time fiscal receipt printing and status monitoring.""",
    'description': """
This module provides integration between Odoo POS and fiscal printers
supported by ErpNet.FP server. Features include:

* Real-time fiscal receipt printing from POS
* Direct browser-to-printer communication for receipts
* Backend support for Z/X reports and administrative operations
* Printer status monitoring
* Automatic fallback to standard printing on error
* Multiple printer support
* Background printer status updates
* Detailed error logging
* Support for different printer models
* Bulgarian tax group mapping (А, Б, В, Г)
* Dual connection mode: Direct (server) and Proxy (browser)
""",
    'version': '18.0.7.0.1',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Point Of Sale',
    "development_status": "Production/Stable",
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'base',
        'bus',
        'mail',
        'point_of_sale',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fiscal_printer_device_cron.xml',
        'views/fiscal_printer_device_views.xml',
        'views/pos_config_view.xml',
        'views/pos_printer_views.xml',
        'views/pos_session_view.xml',
        'views/pos_order_view.xml',
        'views/account_tax_views.xml',
        'views/fiscal_printer_response_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_items.xml',
        'wizard/fiscal_cash_operation_wizard_view.xml',
    ],
    'demo': [
    ],
    'assets': {
        # Backend assets (само за backend, БЕЗ POS зависимости)
        'web.assets_backend': [
            'l10n_bg_erp_net_fp/static/src/js/fiscal_printer_service.js',
            'l10n_bg_erp_net_fp/static/src/js/printer_status_updates.js',
        ],
        # POS assets (само за POS)
        'point_of_sale._assets_pos': [
            'l10n_bg_erp_net_fp/static/src/js/erp_net_fp_printer.js',
            'l10n_bg_erp_net_fp/static/src/js/pos_printer_service.js',
            'l10n_bg_erp_net_fp/static/src/js/payment_screen.js',
            'l10n_bg_erp_net_fp/static/src/js/close_pos_popup_patch.js',
            'l10n_bg_erp_net_fp/static/src/xml/pos_close_popup_template.xml',
            'l10n_bg_erp_net_fp/static/src/js/cash_move_popup.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
