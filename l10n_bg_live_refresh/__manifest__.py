# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Live Refresh (generic bus-driven view refresh)",
    "version": "19.0.2.8.0",
    "category": "Technical",
    "summary": "Generic bus channel + OWL patches that live-reload and flash "
               "backend Form/List views when the server changes records",
    "description": """
Live Refresh
============

A small, generic primitive extracted from l10n_bg_claude_terminal.

Server code calls ``env['live.refresh'].notify(model=, res_ids=, mode=)``
(or ``recs._live_refresh_notify()`` via the ``live.refresh.mixin``).  A bus
message is sent to the affected users; a browser-side service forwards it to
patched Form and List controllers, which reload the matching record or list
and briefly flash the changed fields or highlight the new rows.

This module carries no business logic of its own.  It is meant to be a shared
dependency for any module that needs server-driven live UI refresh
(claude terminal, InfoPay payment status, ErpNet.FP fleet, ...).

Also includes opt-in handlers for POS hardware feeds (barcode reader,
electronic scale) that come over the proxy bus_inject channel —
they dispatch into Odoo's core barcode service and active number
input respectively. A conflict guard short-circuits when Enterprise
``iot`` is installed so we don't double-dispatch each scan / weight.

Toast muting
------------

Proxy events on ``erpnet_fp_proxy_events`` also raise a toast
notification. High-frequency machine feeds (CFX, MQTT) share that
channel with operator-facing events but arrive at tens of events per
second, and their toast body is indistinguishable because the machine
payload carries none of the formatted fields. Set the system parameter::

    l10n_bg_live_refresh.toast_mute_prefixes = cfx.,mqtt.

to suppress the toast for those type prefixes. Empty by default, so
existing databases keep their current behaviour. Muting affects the
toast only — the bus events keep flowing, so dashboards, Shop Floor
and the typed ``BARCODE_SCANNED`` / ``SCALE_READ`` events are
unaffected.
""",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "license": "LGPL-3",
    "depends": ["web", "bus"],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_live_refresh/static/src/scss/live_refresh.scss",
            "l10n_bg_live_refresh/static/src/js/live_refresh_service.js",
            "l10n_bg_live_refresh/static/src/js/live_refresh_controllers.js",
            "l10n_bg_live_refresh/static/src/js/barcode_handler.js",
            "l10n_bg_live_refresh/static/src/js/scale_handler.js",
        ],
    },
    "installable": True,
}
