# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'ErpNet.FP Fiscal Printer for odoo',
    'summary': """
        Integration with ERP.BG fiscal printers through ErpNet.FP server.
        Supports real-time fiscal receipt printing and status monitoring.""",
    'description': """
                           This module provides integration between Odoo POS and fiscal printers
                           supported by ErpNet.FP server. Features include:

                           * Real-time fiscal receipt printing
                           * Printer status monitoring
                           * Automatic receipt reprint on error
                           * Multiple printer support
                           * Background printer status updates
                           * Detailed error logging
                           * Support for different printer models
                       """,
    'version': '18.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Point Of Sale',
    'development_status': 'Beta',
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'base',
        'bus',
        'mail',
        'point_of_sale'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fiscal_printer_device_cron.xml',
        'views/fiscal_printer_device_views.xml',
        'views/fiscal_printer_status_views.xml',
        'views/pos_config_view.xml',
        'views/res_config_settings_views.xml',
        'views/pos_order_view.xml',
        'views/account_tax_views.xml',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_bg_erp_net_fp/static/src/js/printer_status_updates.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
