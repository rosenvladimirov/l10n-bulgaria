# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'ErpNet.FP Fleet — CFX (IPC-2591) Plugin',
    'summary': """
        ONE unified CFX-IPC plugin for ALL shop-floor machines
        (Europlacer placement, PARMI SPI/AOI, reflow oven, lasers).
        Live WS → uniform mrp.workorder population; REST/audit →
        machine-kind-routed statistics.""",
    'description': """
CFX-IPC (IPC-2591) plug-in for ErpNet.FP Fleet — the SINGLE CFX client
for every shop-floor machine. CFX is one standard for all machines;
machine differences live in the CFX message content + the REST
stat-handler routing, NOT in separate addons.

Models:
- cfx.endpoint — one AMQP/CFX subscription target (broker or P2P);
  get_config_payload() feeds the proxy's push_config command.
- cfx.endpoint.template — pre-seeded machine-type catalog.
- cfx.machine.stat — generic per-message statistic record for
  parmi/oven/laser/generic machines.

Ingest:
- POST /erpnet_fp/cfx/ingest (HMAC-signed, same scheme as bus_inject).
  Dispatches by machine_kind to per-machine handlers:
    europlacer → europlacer.trac/.line (soft dep mrp_europlacer_trac)
    parmi/oven/laser/generic → cfx.machine.stat

Live:
- WS/live path populates mrp.workorder UNIFORMLY for every machine via
  the erpnet_fp_proxy_events bus channel + data._refresh hints
  (l10n_bg_live_refresh renders the frontend — zero new JS).
    """,
    'version': '19.0.1.3.0',
    'author': 'Rosen Vladimirov',
    'license': 'AGPL-3',
    'category': 'Manufacturing/IoT',
    'depends': [
        'l10n_bg_erp_net_fp_fleet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/cfx_endpoint_views.xml',
        'views/cfx_endpoint_template_views.xml',
        'views/cfx_machine_stat_views.xml',
        'views/cfx_inspection_views.xml',
        'data/cfx_endpoint_templates.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
