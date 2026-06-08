# Copyright 2025 Rosen Vladimirov
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': 'ErpNet.FP — OCA IoT bridge (Community)',
    'summary': """
        CE-friendly bridge between l10n_bg_erp_net_fp and OCA's
        iot_oca module. Auto-installs when both are present.""",
    'description': """
Drop-in equivalent of `l10n_bg_erp_net_fp_iot` (which depends on the
Enterprise `iot` module) for Community installs that pull in OCA's
`iot_oca` instead. Provides the same end-user features:

* Mirror an `iot.communication.system` (OCA's analogue of EE `iot.box`)
  from a `fiscal.printer.device` — adds `erp_net_fp_url` /
  `erp_net_fp_ssl_verify` fields, plus a one-click "Create matching
  IoT system" header button on the device form
* `iot.device.read_weight()` synchronous helper — calls the ErpNet.FP
  HTTP `/scales/{id}` endpoint and parses the response (no browser
  proxy / bus.bus indirection — the EE bridge needed those because
  EE iot.box assumes the box is in a private network; OCA's flat
  model lets the Odoo backend hit the proxy directly)
* Phase 3 packaging weight QC — abstract weighable mixin + MO /
  picking integration + per-company defaults — identical user flow
  to the EE bridge, calls `iot.device.read_weight()` the same way

Mutually exclusive with `l10n_bg_erp_net_fp_iot` because OCA's
`iot.device` and EE's `iot.device` collide on `_name`. Only one of
the two can be installed in a given registry — pick whichever IoT
framework matches your edition.

Auto-install: True — installs when `iot_oca` and `l10n_bg_erp_net_fp`
are both present.
""",
    'version': '19.4.11.0.0',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Point Of Sale',
    "development_status": "Production/Stable",
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'iot_oca',
        'mrp',
        'stock',
        'l10n_bg_erp_net_fp',
    ],
    'data': [
        'views/iot_communication_system_views.xml',
        'views/iot_device_views.xml',
        'views/fiscal_printer_device_iot_oca_bridge_views.xml',
        'views/packaging_qc_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
