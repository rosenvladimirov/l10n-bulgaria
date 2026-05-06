"""
Extends `iot.device` with two helpers that the rest of the codebase
(crons, server methods, model actions) can call without caring whether
the underlying IoT Box runs in `direct` or `proxy` mode.

Public API:

  device.action_via_proxy(payload, timeout=30) -> dict
      Server-side dispatch. Returns the IoT Box's response for the
      action — works in both direct and proxy modes.

  device.read_weight() -> float | None
      Convenience for scale-type devices: builds the right payload
      and returns just the numeric kg value.

The proxy-mode wire format mirrors fiscal.printer.device exactly so the
`fiscal_browser_proxy_action.js` client and the new iot_longpolling
patch use the same bus channel: `iot.device.request`. Browsers
subscribe to that channel; when a message arrives matching one of
their iot.box hosts, they fetch the URL and POST the result into
iot.device.response.
"""

import json
import logging
import time
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Bus channel name — separate from `fiscal.printer.request` so the two
# legacy and new flows don't compete for the same browser handler.
IOT_BUS_CHANNEL = "iot.device.request"


class IotDevice(models.Model):
    _inherit = "iot.device"

    # ─── Public API ──────────────────────────────────────────────

    def action_via_proxy(self, payload, timeout=30):
        """Run an action on the device, returning its response dict.

        Routes through `direct` or `proxy` mode based on the parent
        iot.box.connection_mode field. In `direct` mode this is a
        plain HTTP request from the Odoo server. In `proxy` mode the
        request is signalled to a connected browser via bus.bus and
        the browser's response is read from iot.device.response.

        :param payload: dict, the inner `data` shape that ErpNet.FP
                        expects (e.g. {"action": "read_once"}).
        :param timeout: seconds to wait for a response.
        :return: dict — the response from the IoT Box / ErpNet.FP.
        :raises UserError: on timeout or transport failure.
        """
        self.ensure_one()
        box = self.iot_id
        if not box:
            raise UserError(_("Device %s has no IoT Box configured") % self.name)
        mode = getattr(box, "connection_mode", "direct")
        if mode == "direct":
            return self._action_via_direct(payload, timeout)
        return self._action_via_browser_proxy(payload, timeout)

    def read_weight(self):
        """Convenience for scale-type devices. Returns kg as float or
        None on failure. Use this in MO / picking weight verification
        flows."""
        self.ensure_one()
        if self.type != "scale":
            raise UserError(_("Device %s is not a scale (type=%s)") %
                            (self.name, self.type))
        result = self.action_via_proxy({"action": "read_once"}, timeout=10)
        # ErpNet.FP returns {"result": <kg>, "status": {"status": "success"}}
        # Native iot box returns same shape.
        if not isinstance(result, dict):
            return None
        status = result.get("status") or {}
        if isinstance(status, dict) and status.get("status") == "error":
            return None
        weight = result.get("result")
        if isinstance(weight, (int, float)):
            return float(weight)
        return None

    # ─── Direct mode — plain HTTP from server ────────────────────

    def _action_via_direct(self, payload, timeout):
        """Server-side fetch of `/hw_drivers/action`. Used when the
        Odoo server sees the IoT Box on its network."""
        import requests
        box = self.iot_id
        base_url = box._get_erp_net_fp_base_url()
        if not base_url:
            raise UserError(_("IoT Box %s has no URL configured") % box.name)
        url = f"{base_url.rstrip('/')}/iot_drivers/action"
        body = {
            "session_id": uuid.uuid4().hex,
            "device_identifier": self.identifier,
            "data": payload,
        }
        verify = getattr(box, "erp_net_fp_ssl_verify", False)
        try:
            resp = requests.post(url, json=body, timeout=timeout, verify=verify)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            _logger.warning("IoT direct call to %s failed: %s", url, exc)
            raise UserError(_(
                "Could not reach IoT Box %(name)s at %(url)s — %(err)s"
            ) % {"name": box.name, "url": url, "err": exc})
        # Native iot wire shape: {"result": {...inner...}}.
        return data.get("result") if isinstance(data, dict) else data

    # ─── Proxy mode — server → browser via bus → ErpNet.FP ───────

    def _action_via_browser_proxy(self, payload, timeout):
        """Send a bus.bus message and poll iot.device.response for the
        matching request_id."""
        request_id = uuid.uuid4().hex
        message = {
            "type": "iot_device_action",
            "request_id": request_id,
            "iot_device_id": self.id,
            "iot_box_id": self.iot_id.id,
            "device_identifier": self.identifier,
            "host": self.iot_id._get_erp_net_fp_base_url(),
            "ssl_verify": getattr(self.iot_id, "erp_net_fp_ssl_verify", False),
            "data": payload,
        }
        # Single broadcast channel; every connected browser handles it
        # and the first one with reachability wins. iot.device.response
        # has a unique request_id so duplicates are harmless.
        self.env["bus.bus"]._sendone(IOT_BUS_CHANNEL, IOT_BUS_CHANNEL, message)
        self.env.cr.commit()  # ensure the bus message hits Postgres NOW

        Response = self.env["iot.device.response"]
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = Response.search(
                [("request_id", "=", request_id),
                 ("iot_device_id", "=", self.id)],
                limit=1,
            )
            if response:
                ok = response.success
                data = response.get_data()
                err = response.error_message or ""
                response.unlink()
                if not ok:
                    raise UserError(_(
                        "IoT proxy returned error for %(name)s: %(err)s"
                    ) % {"name": self.name, "err": err or "unknown"})
                # Match the direct-mode return shape.
                return data.get("result") if isinstance(data, dict) and "result" in data else data
            self.env.cr.commit()  # let other transactions write the response row
            time.sleep(0.4)

        raise UserError(_(
            "Timeout waiting for IoT proxy response from %(name)s after "
            "%(t)ds. Make sure a browser tab with this Odoo session is "
            "open on a machine that can reach %(host)s."
        ) % {"name": self.name, "t": timeout,
             "host": self.iot_id._get_erp_net_fp_base_url() or "?"})
