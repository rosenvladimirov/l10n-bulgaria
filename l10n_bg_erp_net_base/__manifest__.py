# Copyright 2025 Rosen Vladimirov
# License LGPL-3
{
    'name': 'ErpNet.FP — Proxy transport core',
    'summary': """
        Generic Odoo.ErpNet.FP hardware-proxy transport: device record,
        HTTP/WebSocket request layer, connection check, status heartbeat.
        No POS, no account, no fiscal logic.""",
    'description': """
Generic transport core for the Odoo.ErpNet.FP hardware proxy.

Defines the ``fiscal.printer.device`` record (host, connection mode,
direct/browser-proxy HTTP request layer, proxy status heartbeat) plus the
``fiscal.printer.response`` and ``fiscal.printer.status`` helper models and
the browser-proxy controller routes.

This is the shared base beneath the ErpNet.FP consumer plugins:

* ``l10n_bg_erp_net_fp`` — Bulgarian fiscal printer + External-POS layer
* ``l10n_bg_erp_net_reader`` — barcode reader consumer
* ``l10n_bg_erp_net_scale`` — weighing scale consumer

It intentionally depends only on ``base``/``bus``/``mail`` so it can be
installed WITHOUT ``point_of_sale``/``account`` — e.g. on a manufacturing
site that only needs the reader/scale over the proxy.

The model name ``fiscal.printer.device`` is kept for data compatibility with
existing deployments (the fiscal-printer logic lives in the fp plugin).
""",
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Point Of Sale',
    'development_status': 'Beta',
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'base',
        'bus',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fiscal_printer_cron.xml',
        'views/fiscal_printer_device_views.xml',
        'views/fiscal_printer_response_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_bg_erp_net_base/static/src/services/proxy_host.js',
            'l10n_bg_erp_net_base/static/src/js/fiscal_printer_service.js',
            'l10n_bg_erp_net_base/static/src/js/printer_status_updates.js',
            'l10n_bg_erp_net_base/static/src/js/printer_id_field.js',
            'l10n_bg_erp_net_base/static/src/xml/printer_id_field.xml',
            'l10n_bg_erp_net_base/static/src/js/fiscal_browser_proxy_action.js',
        ],
    },
    'pre_init_hook': '_pre_init_migrate_from_fp',
    'installable': True,
    'auto_install': False,
    'application': False,
}
