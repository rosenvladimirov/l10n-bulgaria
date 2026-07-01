# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3
{
    'name': 'ErpNet.FP — Weighing scale',
    'summary': """
        Weighing scale over the Odoo.ErpNet.FP proxy: on-demand weight
        read service (GET /scales/<id>/weight). No POS required.""",
    'description': """
Weighing-scale consumer for the Odoo.ErpNet.FP hardware proxy.

Provides the ``l10n_bg_erp_net_fp.scale`` frontend service, which reads the
current weight ON DEMAND from the proxy:

    GET /scales                 -> { "<id>": {id, driver, port}, ... }
    GET /scales/<id>/weight     -> { ok, weightKg (alias weight_kg),
                                     status, error }

Consumers call ``await svc.readWeight()`` at the moment the operator needs a
weight (e.g. a Shop Floor "Weigh" button). Direct-proxy equivalent of the
Enterprise ``iot`` + ``pos_iot_adam_scale`` path, with NO IoT Box.

Depends only on the transport core ``l10n_bg_erp_net_base`` — no
``point_of_sale``. Registered into ``web.assets_backend`` so it is available
across the whole backend (including the Shop Floor client action).
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
    ],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'l10n_bg_erp_net_scale/static/src/services/erpnet_scale_service.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
