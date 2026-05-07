# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Command queue for back-channel operations on a proxy.

Pull-model architecture: proxies live behind NAT/firewalls and are
NOT reachable from the central fleet. Instead of HTTPing them
directly, admins enqueue commands here and proxies pick them up on
their next heartbeat (default ≤ 60 s latency).

State machine:
    pending → sent → completed
                  ↘  failed

A proxy receives all `pending` commands in its heartbeat response,
executes them locally using its own admin_token (already on disk),
then POSTs the result to `/erp_net_fp/registry/command-result`.
"""
from __future__ import annotations

import json
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

_KIND_LABELS = [
    ("self_update", "Self-update (compose pull + recreate)"),
    ("get_logs", "Fetch /admin/logs"),
    ("program_vat", "Program VAT rates"),
]


class ErpNetFpProxyCommand(models.Model):
    _name = "erpnet.fp.proxy.command"
    _description = "Queued command for an ErpNet.FP proxy"
    _order = "create_date DESC"
    _inherit = ["mail.thread"]
    _rec_name = "kind"

    proxy_id = fields.Many2one(
        "erpnet.fp.proxy", required=True, ondelete="cascade", index=True,
        tracking=True,
    )
    kind = fields.Selection(
        selection=_KIND_LABELS, required=True, tracking=True,
    )
    payload_json = fields.Text(
        help="JSON-encoded parameters specific to the command kind.",
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("sent", "Sent (awaiting result)"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending", required=True, tracking=True, index=True,
    )
    result_json = fields.Text(readonly=True)
    error = fields.Text(readonly=True)
    sent_at = fields.Datetime(readonly=True)
    completed_at = fields.Datetime(readonly=True)
    summary = fields.Char(compute="_compute_summary", store=True)

    @api.depends("kind", "state", "result_json", "error")
    def _compute_summary(self):
        for c in self:
            if c.state == "failed":
                c.summary = (c.error or "Failed")[:80]
            elif c.state == "completed":
                c.summary = "OK"
            else:
                c.summary = dict(c._fields["state"].selection).get(c.state, "")

    # ─── Helpers used by controller and form actions ────────────

    @api.model
    def _serialize_for_proxy(self, cmd) -> dict:
        """Render a single record as a dict the proxy can consume."""
        try:
            payload = json.loads(cmd.payload_json) if cmd.payload_json else {}
        except (ValueError, TypeError):
            payload = {}
        return {
            "id": cmd.id,
            "kind": cmd.kind,
            "payload": payload,
        }

    def mark_sent(self):
        """Called by the heartbeat controller when commands are
        included in a heartbeat response — flips state pending → sent."""
        self.write({
            "state": "sent",
            "sent_at": fields.Datetime.now(),
        })

    def record_result(self, ok: bool, result: dict | None,
                      error: str | None) -> None:
        """Called by /command-result endpoint when the proxy reports back."""
        self.ensure_one()
        try:
            result_json = json.dumps(result, ensure_ascii=False) if result else ""
        except (TypeError, ValueError):
            result_json = json.dumps({"raw": str(result)})
        self.write({
            "state": "completed" if ok else "failed",
            "result_json": result_json,
            "error": error or "",
            "completed_at": fields.Datetime.now(),
        })
        # Bus notify so the form view / kanban refreshes.
        try:
            self.env["bus.bus"]._sendone(
                "erpnet_fp_fleet", "fleet_update",
                {"kind": "command_result", "id": self.proxy_id.id,
                 "command_id": self.id, "ok": ok},
            )
        except Exception:  # noqa: BLE001
            _logger.exception("Bus notify on command_result failed")
