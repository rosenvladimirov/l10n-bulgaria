# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3
{
    'name': 'ErpNet.FP — Barcode reader',
    'summary': """
        Barcode reader over the Odoo.ErpNet.FP proxy: WebSocket scan
        service + barcode.rule routing targets. No POS required.""",
    'description': """
Barcode-reader consumer for the Odoo.ErpNet.FP hardware proxy.

Provides the ``l10n_bg_erp_net_fp.reader`` frontend service, which subscribes
to proxy readers over WebSocket (``/readers/<id>/ws``) and emits scan events
``{reader_id, barcode, timestamp}`` on a shared bus. Any consumer (POS,
Shop Floor, backend forms) subscribes without knowing about the hardware.

Also extends ``barcode.rule`` with N routing targets so one scan can be
dispatched into several (model, field, form) slots at once.

Depends only on the transport core ``l10n_bg_erp_net_base`` — no
``point_of_sale``. The service is registered into ``web.assets_backend`` so
it is available across the whole backend (including the Shop Floor client
action), independent of POS.
""",
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Point Of Sale',
    'development_status': 'Beta',
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'l10n_bg_erp_net_base',
        'barcodes',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/barcode_rule_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_bg_erp_net_reader/static/src/services/erpnet_reader_service.js',
        ],
    },
    'pre_init_hook': '_pre_init_migrate_from_fp',
    'installable': True,
    'auto_install': False,
    'application': False,
}
