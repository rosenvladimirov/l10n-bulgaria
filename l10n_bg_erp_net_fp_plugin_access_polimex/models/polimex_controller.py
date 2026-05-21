# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Polimex iCON controller (bridge / RS-485 master).

One record = one Polimex Web Device + one RS-485 controller on its bus.
A Web Device can host up to 31 controllers; if a customer has more than
one, they all get their own row here (different bus_id).

Operator point of view in Odoo is **abstract**:
  * controller name + which proxy owns it,
  * which parts (reader/magnet/motor/sensor/button) hang off it.
The driver detail (IP, RS-485 ID, mode, output channels) sits inside
the controller record and is emitted into the YAML fragment the proxy
consumes — Odoo doesn't simulate the device, it just instructs the
proxy how to talk to it.
"""
from __future__ import annotations

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Controller modes — taken straight from the Polimex Web Module SPA
# (getCtrlModeText). The 31!=e branch is "relay mode" (vendor-specific
# expansion boards); operators in the field overwhelmingly use door mode.
_MODE_SELECTION = [
    ("1", "One Door (1 × 32 relays in relay mode)"),
    ("2", "Two Doors (2 × 16 relays in relay mode)"),
    ("3", "Three Doors (1 × 512 relays in relay mode)"),
    ("4", "Four Doors"),
]

# Transport — how the proxy talks to the Polimex Web Module.
#
#   sdk_pull  — proxy actively POSTs to /sdk/cmd.json on the Web Module
#               whenever it has a command. Real-time (~50ms). Requires
#               a LAN path from proxy → Polimex and an SDK user/password
#               set inside the Polimex UI ('SDK Active' enabled).
#
#   http_push — Polimex actively POSTs to the proxy every interval
#               (default 60s) with events; the proxy returns queued
#               commands in the response. Works through NAT/firewalls
#               but commands are delayed up to the interval. Requires
#               the proxy's public URL and a shared secret set in the
#               Polimex 'HTTP Push' settings.
_TRANSPORT_SELECTION = [
    ("sdk_pull",  "SDK pull (proxy → Polimex, real-time)"),
    ("http_push", "HTTP push (Polimex → proxy, heartbeat-driven)"),
]


class PolimexController(models.Model):
    _name = "polimex.controller"
    _description = "Polimex iCON Access Controller (RS-485 node)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "proxy_id, bus_id, name"
    _rec_name = "name"

    name = fields.Char(
        required=True, tracking=True,
        help="Operator-friendly label, e.g. 'Front Gate' or 'Warehouse "
             "side entrance'.",
    )
    active = fields.Boolean(default=True, tracking=True)
    proxy_id = fields.Many2one(
        "erpnet.fp.proxy", required=True, ondelete="cascade", tracking=True,
        help="The hardware proxy that talks to this controller's Web "
             "Module. Decides where the regenerated YAML gets pushed.",
    )

    # ─── Transport ──────────────────────────────────────────────
    transport_mode = fields.Selection(
        _TRANSPORT_SELECTION, default="sdk_pull", required=True,
        tracking=True,
        help="Pick how the proxy talks to this Polimex Web Module. "
             "Switch any time; YAML regeneration emits the right "
             "fields for the chosen mode.",
    )

    # ─── Bridge — Polimex Web Device (SDK pull mode) ────────────
    host = fields.Char(
        string="Web Module URL", tracking=True,
        help="(SDK pull mode) HTTP base URL of the Polimex Web Module, "
             "e.g. http://192.168.3.151. The proxy POSTs to "
             "<host>/sdk/cmd.json when it needs to send a command.",
    )
    sdk_user = fields.Char(
        default="sdk",
        help="(SDK pull mode) Username for the dedicated SDK user "
             "configured inside the Polimex Web UI.",
    )
    sdk_password = fields.Char(
        help="(SDK pull mode) Password for the SDK user.",
    )

    # ─── Bridge — Polimex Web Device (HTTP push mode) ───────────
    convertor_serial = fields.Char(
        string="Convertor serial #", tracking=True,
        help="(HTTP push mode) The bridge's serial number as reported "
             "in the heartbeat body (`convertor` field). Matches the "
             "Polimex to this record on incoming POSTs.",
    )
    shared_secret = fields.Char(
        help="(HTTP push mode) Shared bearer token the proxy expects "
             "in the Authorization header of every incoming heartbeat. "
             "Set the same value inside the Polimex 'HTTP Push' settings.",
    )
    push_interval_seconds = fields.Integer(
        string="Push interval (s)", default=60,
        help="(HTTP push mode) How often the Polimex is expected to "
             "post a heartbeat. Used as the inactivity threshold — "
             "if no heartbeat arrives in 3× this, the controller is "
             "marked unreachable.",
    )

    # ─── RS-485 bus address ─────────────────────────────────────
    bus_id = fields.Integer(
        string="Bus ID", default=1, required=True, tracking=True,
        help="RS-485 controller address (1–31). One Web Module can "
             "host up to 31 controllers; each gets its own row.",
    )
    mode = fields.Selection(
        _MODE_SELECTION, default="1", required=True, tracking=True,
        help="Controller mode — defines how outputs map to doors / relays.",
    )
    relay_ctrl = fields.Boolean(
        string="Relay mode (iCON-R / 110R)",
        help="iCON-R / iCON-110R hardware variants (30/31/32) — outputs "
             "act as standalone relays instead of door locks.",
    )

    # ─── Optional metadata ──────────────────────────────────────
    firmware = fields.Char(
        readonly=True, tracking=True,
        help="Reported by the controller (F0 Info command). Updated "
             "manually or by the future 'Probe' action.",
    )
    pulse_seconds = fields.Float(
        default=3.0, required=True,
        help="Default momentary-open duration (seconds) — applied to "
             "every part on this controller unless overridden.",
    )
    fail_secure = fields.Boolean(
        default=True,
        help="Semantic marker — Odoo always decides; the proxy never "
             "auto-opens. Default ON.",
    )

    # ─── Parts ──────────────────────────────────────────────────
    part_ids = fields.One2many(
        "polimex.part", "controller_id", string="Parts",
        help="Reader / Magnet / Strike / Motor / Sensor / Button — "
             "anything wired to this controller's I/O.",
    )
    part_count = fields.Integer(compute="_compute_part_count", store=False)

    # ─── Link to YAML template fragment ─────────────────────────
    template_id = fields.Many2one(
        "erpnet.fp.proxy.config.template",
        string="Config Template",
        help="The access.yaml fragment this controller contributes to. "
             "When set, 'Regenerate YAML' rewrites this template's "
             "yaml_text from every active polimex.controller pointing "
             "to it.",
    )

    notes = fields.Html()

    @api.depends("part_ids", "part_ids.active")
    def _compute_part_count(self):
        for rec in self:
            rec.part_count = len(rec.part_ids.filtered("active"))

    # ─── YAML emission ──────────────────────────────────────────

    def _bare_host(self) -> str:
        """Return host without scheme/port — the proxy's polimex driver
        builds `http://{host}/sdk/cmd.json` itself, so an input like
        'http://192.168.3.151' would produce 'http://http://...' and
        fail with DNS resolution. Tolerate both forms in the UI by
        normalising here at YAML-emit time.
        """
        import urllib.parse as _u
        raw = (self.host or "").strip()
        if not raw:
            return ""
        # urlparse needs a scheme to extract hostname; assume http if missing.
        parsed = _u.urlparse(raw if "://" in raw else "http://" + raw)
        return parsed.hostname or raw.split(":")[0]

    def _yaml_entries(self):
        """One controller often contributes MULTIPLE access entries
        (one per door/output that has a magnet/strike/motor part). The
        proxy doesn't model "controller + parts" — it just wants flat
        `access:` entries keyed by id.

        For each active part of an output type (magnet/strike/motor),
        emit one entry. Reader/sensor/button are inputs / events and
        don't get their own access entry — they're tracked in notes
        for the operator.
        """
        self.ensure_one()
        entries = []
        output_kinds = ("magnet", "strike", "motor")
        is_push = self.transport_mode == "http_push"
        for part in self.part_ids.filtered(
                lambda p: p.active and p.kind in output_kinds):
            entry = {
                "id": part.access_id or part.name,
                "driver": "polimex",
                "transport": self.transport_mode or "sdk_pull",
                "bus_id": self.bus_id,
                "output": part.io_channel,
                "mode": int(self.mode or "1"),
                "relay_ctrl": bool(self.relay_ctrl),
                "pulse_seconds": float(self.pulse_seconds or 3.0),
                "fail_secure": bool(self.fail_secure),
            }
            if is_push:
                # Polimex initiates; proxy is the server. Identify the
                # bridge by serial so heartbeats from this Polimex map
                # back to this access entry.
                entry["convertor_serial"] = self.convertor_serial or ""
                entry["shared_secret"] = self.shared_secret or ""
                entry["push_interval_seconds"] = self.push_interval_seconds or 60
            else:
                # SDK pull — proxy calls Polimex directly. Outbound
                # auth is HTTP Basic with the SDK user/password.
                entry["host"] = self.host or ""
                entry["user"] = self.sdk_user or "sdk"
                entry["password"] = self.sdk_password or ""
            entries.append(entry)
        return entries

    def action_regenerate_yaml(self):
        """Collect all active controllers pointing at template_id and
        emit a fresh access: list. Operators then click Push on the
        template form to actually send it.
        """
        try:
            import yaml as _yaml
        except ImportError as e:
            raise UserError(_(
                "PyYAML is required. Install python3-yaml on the Odoo host."
            )) from e

        templates_by_id = {}
        for rec in self:
            if not rec.template_id:
                raise UserError(_(
                    "Controller %s has no config template assigned.",
                    rec.name))
            templates_by_id.setdefault(rec.template_id.id, rec.template_id)

        if not templates_by_id:
            return

        Ctrl = self.env["polimex.controller"]
        updated = []
        for tmpl in templates_by_id.values():
            siblings = Ctrl.search([
                ("template_id", "=", tmpl.id),
                ("active", "=", True),
            ])
            entries = []
            for ctrl in siblings:
                entries.extend(ctrl._yaml_entries())
            payload = {"access": entries}
            yaml_text = _yaml.safe_dump(
                payload, sort_keys=False, allow_unicode=True)
            tmpl.write({"yaml_text": yaml_text})
            updated.append(tmpl.display_name)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("YAML regenerated"),
                "message": _("Templates updated: %s",
                             ", ".join(updated) or _("(none)")),
                "type": "success",
                "sticky": False,
            },
        }

    def action_open_parts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Parts"),
            "res_model": "polimex.part",
            "view_mode": "list,form",
            "domain": [("controller_id", "=", self.id)],
            "context": {"default_controller_id": self.id},
        }

    def action_open_template(self):
        self.ensure_one()
        if not self.template_id:
            raise UserError(_(
                "Controller %s has no template assigned. Create one "
                "first under Fleet → Settings → Devices.",
                self.name))
        return {
            "type": "ir.actions.act_window",
            "name": _("Config Template"),
            "res_model": "erpnet.fp.proxy.config.template",
            "view_mode": "form",
            "res_id": self.template_id.id,
        }
