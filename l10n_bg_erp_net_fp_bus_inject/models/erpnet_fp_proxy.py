# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later.
"""Inject Test Event — operator-side button on the proxy form.

Hits OUR OWN /erpnet_fp/bus/inject endpoint from the Odoo backend
with a hand-crafted envelope, properly HMAC-signed. Lets operators
prove the full pipeline (bus_inject → live_refresh hub → toast)
without needing the hardware proxy to actually run a Polimex call.

Useful for:
  * Demo / training (no hardware)
  * Fleet-side CI smoke tests
  * Debugging the toast UI / dashboard listeners
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _iso_utc_ms() -> str:
    return (datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"))


class ErpNetFpProxy(models.Model):
    _inherit = "erpnet.fp.proxy"

    def action_inject_test_event(self):
        """Send a synthetic `door.opened` envelope to our own bus_inject
        endpoint, signed with this proxy's registry_secret. Same path
        a real proxy would take — Odoo just plays both sides of the
        wire for demonstration.
        """
        self.ensure_one()
        if not self.registry_secret:
            raise UserError(_(
                "Proxy %s has no registry_secret — it must complete "
                "auto-enrol or pairing before bus_inject can be tested.",
                self.name))

        # Pick our OWN base URL — the same one a real proxy hits.
        base = (
            self.env["ir.config_parameter"].sudo()
            .get_param("web.base.url", default="")
            .rstrip("/"))
        if not base:
            raise UserError(_(
                "ir.config_parameter web.base.url is empty — cannot "
                "derive bus_inject URL."))

        envelope = {
            "v": 1,
            "type": "door.opened",
            "source": {
                "proxy": self.name,
                "device": "test-magnet",
                "device_kind": "access",
            },
            "ts": _iso_utc_ms(),
            "id": str(uuid.uuid4()),
            "data": {
                "seconds": 3,
                "state": "open",
                "detail": "synthetic test from Odoo Inject Test Event",
            },
        }
        body = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
        sig = hmac.new(
            self.registry_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        try:
            r = requests.post(
                f"{base}/erpnet_fp/bus/inject",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Bus-Inject-Signature": sig,
                    "X-Bus-Inject-Proxy": self.name,
                },
                timeout=8.0,
            )
        except requests.RequestException as e:
            raise UserError(_(
                "Could not reach %(u)s: %(e)s", u=base, e=e)) from e
        if r.status_code != 200:
            raise UserError(_(
                "bus_inject endpoint returned HTTP %(s)d: %(b)s",
                s=r.status_code, b=r.text[:400]))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Test event injected"),
                "message": _(
                    "%(t)s event published on channel "
                    "erpnet_fp_proxy_events — watch the toast and any "
                    "open dashboard.",
                    t=envelope["type"]),
                "type": "success",
                "sticky": False,
            },
        }
