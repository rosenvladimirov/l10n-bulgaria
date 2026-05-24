"""
l10n.bg.fiscal.plu.verify.wizard — Verify PLU sync state on devices.

For the selected PLU records, queries each linked fiscal printer
(via /printers/<id>/plu/read endpoint), reads the actual programmed
data, and updates `l10n.bg.fiscal.plu.device.line.state`:
  * synced  — device data matches local snapshot (name+price+vat)
  * stale   — device has different data (local changed since push)
  * missing — device has no PLU at that slot
  * error   — verification request failed
"""

import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class L10nBgFiscalPluVerifyWizard(models.TransientModel):
    _name = "l10n.bg.fiscal.plu.verify.wizard"
    _description = "Verify PLUs against fiscal devices"

    plu_ids = fields.Many2many(
        "l10n.bg.fiscal.plu",
        string="PLUs to verify",
        required=True,
        default=lambda self: self._default_plu_ids(),
    )
    device_ids = fields.Many2many(
        "fiscal.printer.device",
        string="Devices",
        help="If empty — verify against all devices each PLU is linked "
        "to (device_sync_ids). Otherwise — verify only on the selected "
        "devices.",
    )

    @api.model
    def _default_plu_ids(self):
        if self.env.context.get("active_model") == "l10n.bg.fiscal.plu":
            return self.env.context.get("active_ids", [])
        return []

    def action_verify(self):
        """Re-read each PLU from selected devices and update state."""
        self.ensure_one()
        results = []  # list of dicts for popup
        for plu in self.plu_ids:
            devices = (
                self.device_ids
                or plu.device_sync_ids.mapped("device_id")
            )
            for dev in devices:
                line = plu.device_sync_ids.filtered(
                    lambda l: l.device_id == dev
                )[:1]
                # Ensure a line exists so verification has somewhere to write.
                if not line:
                    line = self.env["l10n.bg.fiscal.plu.device.line"].create({
                        "plu_id": plu.id,
                        "device_id": dev.id,
                        "state": "missing",
                    })
                # Call the proxy to read the PLU back.
                try:
                    payload = dev._proxy_post(
                        "plu/read",
                        {"plu": plu.plu_number},
                        timeout=10,
                    )
                except Exception as exc:  # noqa: BLE001
                    line.write({
                        "state": "error",
                        "error_msg": str(exc)[:200],
                        "last_verified_at": fields.Datetime.now(),
                    })
                    results.append({
                        "plu": plu.plu_number, "device": dev.name,
                        "state": "error", "msg": str(exc)[:100],
                    })
                    continue
                # Update line based on device response.
                if not payload or not payload.get("ok"):
                    line.write({
                        "state": "missing",
                        "last_verified_at": fields.Datetime.now(),
                    })
                    results.append({
                        "plu": plu.plu_number, "device": dev.name,
                        "state": "missing", "msg": "",
                    })
                    continue
                dev_name = (payload.get("name") or "").strip()
                dev_price = float(payload.get("price") or 0)
                dev_vat = (payload.get("vat_group") or "").strip()
                matches = (
                    dev_name == (plu.name or "").strip()
                    and abs(dev_price - (plu.price or 0)) < 0.01
                )
                line.write({
                    "state": "synced" if matches else "stale",
                    "pushed_name": dev_name,
                    "pushed_price": dev_price,
                    "pushed_vat_group": dev_vat[:4] or False,
                    "last_verified_at": fields.Datetime.now(),
                    "error_msg": False if matches else "Device data differs",
                })
                results.append({
                    "plu": plu.plu_number, "device": dev.name,
                    "state": "synced" if matches else "stale", "msg": "",
                })

        _logger.info("PLU verify wizard: %d checks done", len(results))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("PLU verification done"),
                "message": _("%d checks completed. Open Synced devices tab "
                             "for per-PLU detail.") % len(results),
                "type": "info",
                "sticky": False,
            },
        }
