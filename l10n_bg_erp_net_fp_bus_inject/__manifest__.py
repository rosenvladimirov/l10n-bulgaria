# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    'name': 'ErpNet.FP Bus Inject — proxy → Odoo live events',
    'summary': """
        Standardised JSON envelope + WebSocket bus channel for live event
        push from the Odoo.ErpNet.FP hardware proxy to Odoo backend +
        frontend subscribers. No DB record on each event; pure live signal.""",
    'description': """
Defines and serves ONE canonical JSON push channel for the hardware
proxy:

  Channel:   "erpnet_fp_proxy_events" (bus.bus, broadcast)
  Endpoint:  POST /erpnet_fp/bus/inject (HMAC-signed body)
  Envelope:  {v, type, source, ts, id, data}

The proxy POSTs an envelope; the controller verifies HMAC against the
sending proxy's registry_secret (same auth pattern as the Fleet
heartbeat), stamps server-side ts + id, and publishes onto the bus.
No DB record is created — bus_inject is purely a live signal channel.

Use cases for live signal (no persistence):
  * Plate just seen on a parking-lot camera — show toast on dashboard
  * RFID card just scanned — flash the door open status
  * Polimex controller heartbeat — keep an "alive" badge fresh
  * Door sensor changed — animate the door icon on the floor-plan view

For audit-grade events that MUST persist, the proxy still uses the
existing HTTP-with-record path (POST /lpr_gateway, /access/event,
etc.) — bus_inject is the additive live-only twin.

Schema reference: see `docs/proxy_push_schema.md` inside this module
(also rendered in `static/description/index.html` for the app drawer).

Depends:
  * l10n_bg_erp_net_fp_fleet — for the proxy registry + HMAC-verify
    helper. No code coupling beyond import of `_verify_hmac`.
""",
    'version': '18.0.1.2.0',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Hardware/Fleet/Plugins',
    "development_status": "Alpha",
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'l10n_bg_erp_net_fp_fleet',  # for erpnet.fp.proxy + registry_secret
        'l10n_bg_live_refresh',       # owns the frontend bus subscription
        'bus',
    ],
    'data': [
        'views/erpnet_fp_proxy_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
