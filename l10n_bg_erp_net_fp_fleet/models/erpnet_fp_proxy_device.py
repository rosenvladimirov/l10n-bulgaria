# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Per-device record synced from heartbeat `devices` payload.

Each row represents a single device (printer / pinpad / scale /
reader / display) attached to a proxy. The heartbeat handler
mirrors the proxy's `devices` dict into these rows so admins can
filter, group and chart by device kind across the whole fleet:

    Fleet → Statistics → Devices
        graph (count by kind)
        pivot (proxy × kind)
        list (all devices, filterable)

Devices are matched by (proxy_id, kind, identifier). Missing rows
are auto-archived (active=False) so we don't lose history; new ones
are created. The `last_seen` timestamp tracks freshness for stats.
"""
from __future__ import annotations

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

_KIND_LABELS = [
    ("printer", "Fiscal printer"),
    ("pinpad", "Payment pinpad"),
    ("scale", "Weighing scale"),
    ("reader", "Barcode reader"),
    ("display", "Customer display"),
    ("camera", "Camera"),
    ("access", "Access controller"),
]


class ErpNetFpProxyDevice(models.Model):
    _name = "erpnet.fp.proxy.device"
    _description = "Device attached to an ErpNet.FP proxy"
    _order = "kind, identifier"
    _rec_name = "identifier"

    proxy_id = fields.Many2one(
        "erpnet.fp.proxy", required=True, ondelete="cascade", index=True,
    )
    proxy_name = fields.Char(
        related="proxy_id.name", store=True, readonly=True,
    )
    proxy_alive = fields.Boolean(
        related="proxy_id.alive", store=False, readonly=True,
    )
    kind = fields.Selection(
        selection=_KIND_LABELS, required=True, index=True,
    )
    identifier = fields.Char(
        required=True, index=True,
        help="Device id as configured on the proxy "
             "(e.g. 'dp150', 'bt1', 'cas1').",
    )
    first_seen = fields.Datetime(default=fields.Datetime.now, readonly=True)
    last_seen = fields.Datetime(default=fields.Datetime.now, readonly=True)
    active = fields.Boolean(default=True, index=True)

    _sql_constraints = [
        ("proxy_kind_id_uniq",
         "UNIQUE(proxy_id, kind, identifier)",
         "A device with this kind/identifier already exists for this proxy."),
    ]

    # ─── Heartbeat sync ─────────────────────────────────────────

    @api.model
    def _sync_from_heartbeat(self, proxy, devices_payload: dict) -> None:
        """Reflect `devices_payload` (`{printers: [..], pinpads: [..], ...}`)
        into rows. Adds new ones, refreshes last_seen, archives ones
        that disappeared from this heartbeat (proxy operator removed
        them from config.yaml).
        """
        now = fields.Datetime.now()
        plural_to_singular = {
            "printers": "printer",
            "pinpads": "pinpad",
            "scales": "scale",
            "readers": "reader",
            "displays": "display",
            "cameras": "camera",
            "access": "access",
        }
        seen_keys = set()
        for plural, ids in (devices_payload or {}).items():
            kind = plural_to_singular.get(plural)
            if not kind:
                continue
            for ident in ids or []:
                if not ident:
                    continue
                seen_keys.add((kind, str(ident)))

        existing = self.with_context(active_test=False).search(
            [("proxy_id", "=", proxy.id)])
        existing_map = {(r.kind, r.identifier): r for r in existing}

        to_create = []
        for kind, ident in seen_keys:
            row = existing_map.get((kind, ident))
            if row:
                vals = {"last_seen": now}
                if not row.active:
                    vals["active"] = True
                row.write(vals)
            else:
                to_create.append({
                    "proxy_id": proxy.id,
                    "kind": kind,
                    "identifier": ident,
                    "first_seen": now,
                    "last_seen": now,
                })
        if to_create:
            self.create(to_create)

        # Archive devices that disappeared from the heartbeat — keep
        # history for trend analysis instead of unlinking.
        gone = [(k, i) for (k, i) in existing_map if (k, i) not in seen_keys]
        for k, i in gone:
            row = existing_map[(k, i)]
            if row.active:
                row.active = False
