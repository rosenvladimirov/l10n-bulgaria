"""
Bridge between `fiscal.printer.device` (CE-compatible core) and OCA's
`iot.communication.system` / `iot.device`.

Same UX as the EE bridge: a one-click button on the device form spawns
an iot.communication.system that mirrors host / ssl_verify, plus an
iot.device with `erp_net_fp_kind = "printer"`. Subsequent host /
ssl_verify edits on the device propagate to the linked system.
"""

import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class FiscalPrinterDeviceIotOcaBridge(models.Model):
    _inherit = "fiscal.printer.device"

    iot_communication_system_id = fields.Many2one(
        "iot.communication.system",
        string="IoT system (OCA)",
        help="Optional link to an OCA iot.communication.system record. "
             "When set, the system's erp_net_fp_url + ssl_verify track "
             "this device's host + ssl_verify on every write. Created "
             "on demand by the 'Create matching IoT system' button; "
             "safe to delete the link without affecting the legacy "
             "fiscal.printer.device flow.",
    )

    def action_create_matching_iot_oca_system(self):
        """Spawn an iot.communication.system mirroring this device,
        plus a printer-typed iot.device under it. Idempotent — re-runs
        update existing records instead of creating duplicates."""
        self.ensure_one()
        System = self.env["iot.communication.system"].sudo()
        Device = self.env["iot.device"].sudo()

        identifier = f"printer.{self.printer_id}"
        system = self.iot_communication_system_id
        if not system:
            system = System.create({
                "name": self.name,
                "erp_net_fp_url": self.host,
                "erp_net_fp_ssl_verify": self.ssl_verify,
                "fiscal_printer_device_id": self.id,
            })
            self.iot_communication_system_id = system

        system.write({
            "erp_net_fp_url": self.host,
            "erp_net_fp_ssl_verify": self.ssl_verify,
        })

        existing = Device.search([
            ("communication_system_id", "=", system.id),
            ("erp_net_fp_identifier", "=", identifier),
        ], limit=1)
        if not existing:
            Device.create({
                "communication_system_id": system.id,
                "name": f"{self.name} (printer)",
                "model": "ErpNet.FP fiscal printer",
                "ip": _hostname_only(self.host),
                "erp_net_fp_kind": "printer",
                "erp_net_fp_identifier": identifier,
            })

        return {
            "type": "ir.actions.act_window",
            "res_model": "iot.communication.system",
            "res_id": system.id,
            "view_mode": "form",
            "target": "current",
        }

    def write(self, vals):
        """Mirror host / ssl_verify changes to the linked OCA system."""
        result = super().write(vals)
        sync_keys = {"host", "ssl_verify"}
        if sync_keys.intersection(vals.keys()):
            for rec in self:
                system = rec.iot_communication_system_id
                if not system:
                    continue
                system.sudo().write({
                    "erp_net_fp_url": rec.host,
                    "erp_net_fp_ssl_verify": rec.ssl_verify,
                })
        return result


def _hostname_only(url):
    """Strip scheme + path → keep just hostname[:port] for iot.device.ip."""
    if not url:
        return ""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.hostname or url
        if parsed.port and parsed.port not in (80, 443):
            return f"{host}:{parsed.port}"
        return host
    except Exception:
        return url
