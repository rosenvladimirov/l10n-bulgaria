# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Polimex controller part — a single function on a controller's I/O.

For the Odoo operator, the access controller breaks into discrete
parts: magnet/strike on output #1, motor on output #2, reader on
input #3, etc. Each row here is one such function.

Output parts (magnet/strike/motor) become access entries in the
proxy's access.yaml — they're things the controller can ACTUATE.

Input parts (reader/sensor/button) are documentation only; the
controller reports their state through F5/B3 event commands, and the
proxy decides what to do with them based on Odoo policy.
"""
from __future__ import annotations

from odoo import api, fields, models


_KIND_SELECTION = [
    ("magnet", "Electromagnetic lock"),
    ("strike", "Electric strike"),
    ("motor", "Gate motor"),
    ("reader", "RFID / keypad reader"),
    ("sensor", "Door / motion sensor"),
    ("button", "Exit button / REX"),
]

# Sub-set that emits a proxy access entry — outputs the controller
# can ACTUATE. Inputs are observed, not written.
_OUTPUT_KINDS = ("magnet", "strike", "motor")


class PolimexPart(models.Model):
    _name = "polimex.part"
    _description = "Polimex Controller Part (one I/O function)"
    _order = "controller_id, sequence, io_channel, kind"
    _rec_name = "display_name"

    controller_id = fields.Many2one(
        "polimex.controller", required=True, ondelete="cascade",
        index=True,
    )
    name = fields.Char(
        required=True,
        help="Operator label — 'Front gate magnet', 'Lobby reader', etc.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    kind = fields.Selection(
        _KIND_SELECTION, required=True, default="magnet",
        help="What this part does. Outputs (magnet/strike/motor) become "
             "access.yaml entries; inputs (reader/sensor/button) are "
             "documentation only — the proxy observes them through the "
             "controller's event stream.",
    )
    io_channel = fields.Integer(
        string="I/O Channel",
        default=1, required=True,
        help="Output number on the controller (1..N depending on mode), "
             "or input number for sensor/reader/button.",
    )
    access_id = fields.Char(
        string="Access ID",
        help="Stable id used in the proxy's access.yaml. Defaults to "
             "`name` if empty. Must be unique across the whole proxy "
             "(not just this controller).",
    )
    notes = fields.Text()

    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("kind", "io_channel", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.kind or '?'}#{rec.io_channel or '?'} · {rec.name or ''}"
            ).strip(" ·")

    @api.depends("kind")
    def _compute_is_output(self):
        for rec in self:
            rec.is_output = rec.kind in _OUTPUT_KINDS

    is_output = fields.Boolean(compute="_compute_is_output", store=False)
