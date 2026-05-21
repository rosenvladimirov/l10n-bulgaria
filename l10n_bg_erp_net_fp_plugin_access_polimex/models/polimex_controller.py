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

    # ─── Bridge — Polimex Web Device ────────────────────────────
    host = fields.Char(
        string="Web Module URL", required=True, tracking=True,
        help="HTTP base URL of the Polimex Web Module hosting this "
             "controller, e.g. http://192.168.3.151. SPA + SDK both "
             "live at the same address.",
    )
    sdk_user = fields.Char(default="sdk", required=True)
    sdk_password = fields.Char(
        help="Password for the dedicated SDK user. Set inside the "
             "Polimex Web UI (separate from admin/UI password).",
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
        for part in self.part_ids.filtered(
                lambda p: p.active and p.kind in output_kinds):
            entry = {
                "id": part.access_id or part.name,
                "driver": "polimex",
                "host": self.host or "",
                "user": self.sdk_user or "sdk",
                "password": self.sdk_password or "",
                "bus_id": self.bus_id,
                "output": part.io_channel,
                "mode": int(self.mode or "1"),
                "relay_ctrl": bool(self.relay_ctrl),
                "pulse_seconds": float(self.pulse_seconds or 3.0),
                "fail_secure": bool(self.fail_secure),
            }
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
