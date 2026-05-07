"""
Extends OCA's `iot.device` with ErpNet.FP-specific fields and a
`read_weight()` helper that the Phase 3 packaging-weight QC mixin
calls.

OCA's iot.device has no `type` selection (scale / printer / reader /
...); we add a lightweight `erp_net_fp_kind` Selection so the bridge
can filter scales for the QC mixin's domain.

`read_weight()` makes a synchronous HTTP GET to the parent system's
`erp_net_fp_url` + `/scales/{erp_net_fp_identifier}` and parses the
JSON response. No bus.bus / browser-proxy machinery — the OCA model
is simpler than the EE one and the proxy server is reachable from
the Odoo backend on standard CE deployments.
"""

import json
import logging
from urllib.parse import urljoin

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ERPNET_KIND = [
    ("printer", "Fiscal printer"),
    ("scale", "Weighing scale"),
    ("reader", "Barcode reader"),
    ("pinpad", "PIN pad"),
    ("display", "Customer display"),
]


class IoTDevice(models.Model):
    _inherit = "iot.device"

    erp_net_fp_kind = fields.Selection(
        ERPNET_KIND,
        string="ErpNet.FP device kind",
        help="Which class of ErpNet.FP-served peripheral this is. "
             "Lets the packaging weight QC mixin filter for scales, "
             "and the bridge views pick the right form fields.",
    )
    erp_net_fp_identifier = fields.Char(
        string="ErpNet.FP identifier",
        help="Key under which the device is registered on the "
             "ErpNet.FP server, e.g. `scale1` or `printer.DT519823`. "
             "Sent to /<endpoint>/{identifier} URLs.",
    )

    # ─── Public API used by packaging weight QC ────────────────────

    def read_weight(self):
        """Synchronous read of the current weight (kg) from a scale.

        Caller contract matches `l10n_bg_erp_net_fp_iot/.../read_weight()`
        from the EE bridge: returns a float (kg) on success, None on
        unstable / unreachable; raises UserError for misconfiguration
        so the QC button surfaces the message clearly.
        """
        self.ensure_one()
        if self.erp_net_fp_kind != "scale":
            raise UserError(_(
                "Device %s is not flagged as an ErpNet.FP scale "
                "(erp_net_fp_kind = %s). Set the kind on the device "
                "form before calling read_weight()."
            ) % (self.name, self.erp_net_fp_kind or "(empty)"))

        system = self.communication_system_id
        url_base = system.erp_net_fp_url if system else None
        if not url_base:
            raise UserError(_(
                "ErpNet.FP URL not set on the parent IoT system %s."
            ) % (system.name if system else "(missing)"))

        identifier = self.erp_net_fp_identifier or self.name
        endpoint = urljoin(
            url_base.rstrip("/") + "/",
            f"scales/{identifier}",
        )
        try:
            resp = requests.get(
                endpoint,
                timeout=3.0,
                verify=bool(system.erp_net_fp_ssl_verify),
            )
        except requests.RequestException as exc:
            _logger.warning(
                "ErpNet.FP read_weight HTTP error for %s: %s",
                self.name, exc,
            )
            return None

        if not resp.ok:
            _logger.warning(
                "ErpNet.FP read_weight HTTP %s for %s: %s",
                resp.status_code, self.name, resp.text[:200],
            )
            return None

        try:
            data = resp.json()
        except (ValueError, json.JSONDecodeError):
            _logger.warning("ErpNet.FP read_weight non-JSON response for %s", self.name)
            return None

        # Server response shape (matches Odoo.ErpNet.FP server.routes.scales):
        #   {"ok": True, "weight_kg": 1.234, "stable": true, "raw": "..."}
        # Returns weight only if stable=True (pass-through if absent → True)
        if not data.get("ok"):
            return None
        if data.get("stable") is False:
            return None
        kg = data.get("weight_kg")
        try:
            return float(kg) if kg is not None else None
        except (TypeError, ValueError):
            return None
