# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': 'ErpNet.FP Fleet Manager',
    'summary': """
        Central control plane for distributed ErpNet.FP proxy instances.""",
    'description': """
Fleet manager for ErpNet.FP fiscal-printer proxies. Each proxy
deployed in a shop heartbeats here every minute with version, host,
and the list of attached devices (printers, pinpads, scales, readers,
displays). Administrators can:

* Generate one-time pairing tokens to enrol new proxies
* Monitor `last_seen` and computed `alive` status
* Trigger remote `/admin/self-update` with one click
* Stream `/admin/logs` from the proxy without shell access
* Program fiscal-printer VAT rates remotely

The proxy's admin token is stored Fernet-encrypted at rest with a
key kept in `ir.config_parameter` (visible only to base.group_system).

This module has NO dependency on `point_of_sale`, `iot`, `mrp`, or
`stock` and is designed to run on a dedicated CE Odoo instance
(default `iot.mcpworks.net`) — the central registry need not also
host the POS that actually uses the printers.
""",
    'version': '19.0.4.2.1',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Hardware/Fleet',
    "development_status": "Beta",
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'base',
        'mail',
        'l10n_bg_live_refresh',
    ],
    'external_dependencies': {
        'python': ['cryptography'],
    },
    'data': [
        'security/erpnet_fp_fleet_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/erpnet_fp_proxy_views.xml',
        'views/erpnet_fp_proxy_device_views.xml',
        'views/erpnet_fp_proxy_config_template_views.xml',
        'wizard/erpnet_fp_program_vat_wizard_views.xml',
        'wizard/erpnet_fp_grab_proxy_wizard_views.xml',
        'views/menu_items.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_bg_erp_net_fp_fleet/static/src/js/fleet_autorefresh.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
