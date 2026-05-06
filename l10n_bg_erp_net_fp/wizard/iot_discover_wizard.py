"""
"Discover devices" wizard for an iot.box that points at an ErpNet.FP
instance.

Click on iot.box.action_open_discover_wizard → opens a transient
wizard that queries the ErpNet.FP REST endpoints (/scales, /displays,
/readers, /printers, /pinpads) and offers to create iot.device
records for everything it finds, with the right `<kind>.<id>`
identifier so the IoT compat layer in ErpNet.FP recognises them.

Existing iot.device records (matched by identifier) are skipped so
re-running the wizard is idempotent.

The wizard is purely additive — it does NOT touch fiscal.printer.device
records or any legacy state.
"""

import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ErpNet.FP endpoint → iot.device.type mapping. Keep in sync with the
# `_split_identifier` table in odoo_erpnet_fp/server/routes/iot_compat.py.
_ENDPOINT_KIND_MAP = [
    ("scales", "scale", "scale"),
    ("displays", "display", "display"),
    ("readers", "scanner", "reader"),
    ("printers", "printer", "printer"),
    ("pinpads", "payment", "pinpad"),
]


class IotDiscoverWizard(models.TransientModel):
    _name = "iot.discover.wizard"
    _description = "Discover ErpNet.FP devices and create iot.device records"

    iot_box_id = fields.Many2one(
        "iot.box",
        string="IoT Box",
        required=True,
        ondelete="cascade",
        default=lambda self: (
            self.env.context.get("active_id")
            if self.env.context.get("active_model") == "iot.box"
            else False
        ),
        help="The iot.box record whose ErpNet.FP URL we'll query. "
             "Auto-populated when the wizard is opened via the "
             "'Discover ErpNet.FP devices' button on an iot.box form.",
    )
    line_ids = fields.One2many(
        "iot.discover.wizard.line",
        "wizard_id",
        string="Discovered devices",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("scanned", "Scanned")],
        default="draft",
    )

    def action_scan(self):
        """Hit ErpNet.FP endpoints and populate `line_ids`."""
        self.ensure_one()
        base_url = self.iot_box_id._get_erp_net_fp_base_url()
        if not base_url:
            raise UserError(_(
                "iot.box %(name)s has no ErpNet.FP URL configured. "
                "Set the `erp_net_fp_url` field first."
            ) % {"name": self.iot_box_id.name or "?"})

        verify = self.iot_box_id.erp_net_fp_ssl_verify
        existing_idents = set(
            self.env["iot.device"].search([
                ("iot_id", "=", self.iot_box_id.id),
            ]).mapped("identifier")
        )

        # Drop any old wizard lines from a previous scan
        self.line_ids.unlink()
        Line = self.env["iot.discover.wizard.line"]
        rows = []
        errors = []

        for endpoint, iot_type, kind in _ENDPOINT_KIND_MAP:
            url = f"{base_url.rstrip('/')}/{endpoint}"
            try:
                resp = requests.get(url, timeout=8, verify=verify)
                resp.raise_for_status()
                payload = resp.json() or {}
            except requests.exceptions.RequestException as exc:
                errors.append(f"{endpoint}: {exc}")
                _logger.warning("Discover %s failed: %s", url, exc)
                continue
            # Endpoints return dict {id: info_dict}.
            if not isinstance(payload, dict):
                continue
            for dev_id, info in payload.items():
                identifier = f"{kind}.{dev_id}"
                rows.append({
                    "wizard_id": self.id,
                    "device_id_in_proxy": str(dev_id),
                    "kind": kind,
                    "iot_type": iot_type,
                    "identifier": identifier,
                    "name_suggestion": _build_name(kind, dev_id, info),
                    "info_summary": _summarise_info(info),
                    "already_exists": identifier in existing_idents,
                    "selected": identifier not in existing_idents,
                })

        if rows:
            Line.create(rows)
        self.state = "scanned"

        if errors:
            self.iot_box_id.message_post(
                body=_("Discovery completed with errors: %s")
                % "; ".join(errors)
            )

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context),
        }

    def action_create_devices(self):
        """Create iot.device records for selected lines."""
        self.ensure_one()
        Device = self.env["iot.device"]
        created = self.env["iot.device"]
        skipped = 0
        for line in self.line_ids.filtered(lambda l: l.selected and not l.already_exists):
            device = Device.create({
                "iot_id": self.iot_box_id.id,
                "name": line.name_suggestion,
                "identifier": line.identifier,
                "type": line.iot_type,
                "connection": "network",
                "connected": True,
                "manufacturer": "ErpNet.FP",
            })
            created |= device
        skipped = len(self.line_ids.filtered("already_exists"))

        # Friendly notification — show count + list, then close wizard.
        msg = _(
            "Created %(c)d new iot.device record(s); skipped %(s)d "
            "already-existing device(s)."
        ) % {"c": len(created), "s": skipped}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("ErpNet.FP discovery complete"),
                "message": msg,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class IotDiscoverWizardLine(models.TransientModel):
    _name = "iot.discover.wizard.line"
    _description = "Discovered ErpNet.FP device — wizard line"

    wizard_id = fields.Many2one(
        "iot.discover.wizard",
        ondelete="cascade",
        required=True,
    )
    device_id_in_proxy = fields.Char(string="ErpNet.FP ID")
    kind = fields.Char(string="Kind")
    iot_type = fields.Char(string="iot.device.type")
    identifier = fields.Char(string="Identifier")
    name_suggestion = fields.Char(string="Name")
    info_summary = fields.Char(string="Details")
    already_exists = fields.Boolean(string="Already configured")
    selected = fields.Boolean(string="Create", default=True)


def _build_name(kind, dev_id, info):
    """Compose a human-readable name from the ErpNet.FP info dict."""
    if not isinstance(info, dict):
        return f"{kind.title()} {dev_id}"
    parts = [kind.title(), str(dev_id)]
    driver = info.get("driver")
    if driver:
        parts.append(f"({driver})")
    return " ".join(parts)


def _summarise_info(info):
    """One-line summary for the wizard list view."""
    if not isinstance(info, dict):
        return ""
    keys = ("driver", "port", "transport", "encoding")
    bits = []
    for k in keys:
        v = info.get(k)
        if v:
            bits.append(f"{k}={v}")
    return " · ".join(bits)
