"""
Append-only audit trail of every command sent to / response received
from a fiscal printer.

Required by Наредба Н-18 (BG fiscalization). Records are NOT deletable
through the ORM (only by the database superuser, intentionally bypassing
this safety net for migrations / GDPR-exempt fiscal-archive purges).

This is a NEW model added by the proxy-aware extension; it does not
touch any existing logic in the addon.
"""

from odoo import _, fields, models
from odoo.exceptions import UserError


class FiscalFrameLog(models.Model):
    _name = "fiscal.frame.log"
    _description = "Fiscal Printer Frame Log (append-only)"
    _order = "id desc"
    _rec_name = "summary"

    timestamp = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    device_id = fields.Many2one(
        "fiscal.printer.device",
        index=True,
        required=True,
        ondelete="restrict",
    )
    pos_order_id = fields.Many2one(
        "pos.order",
        index=True,
        ondelete="set null",
        help="Originating POS order, if any (most fiscal calls are "
        "tied to one). Empty for X/Z reports, cash ops, status checks.",
    )

    direction = fields.Selection(
        [("out", "Host → Device"), ("in", "Device → Host")],
        required=True,
    )
    endpoint = fields.Char(
        help="ErpNet.FP HTTP endpoint that produced this frame, e.g. "
        "'/printers/dp150/receipt'.",
    )
    cmd_name = fields.Char(
        help="Human-readable command label (driver-specific).",
    )
    raw_hex = fields.Char(
        string="Raw bytes (hex)",
        help="Wire bytes for compliance — preserved verbatim.",
    )
    payload = fields.Text(
        help="JSON / human-readable representation of the request or "
        "response body.",
    )
    error_code = fields.Integer(
        help="Non-zero if the device returned a fiscal error.",
    )
    summary = fields.Char(
        compute="_compute_summary",
        store=True,
    )

    def _compute_summary(self):
        for rec in self:
            arrow = "→" if rec.direction == "out" else "←"
            rec.summary = f"{rec.timestamp} {arrow} {rec.endpoint or rec.cmd_name or '?'}"

    def write(self, vals):
        # Append-only safety: only superuser-driven writes (e.g.
        # automated migration scripts) are allowed.
        if not self.env.su:
            raise UserError(
                _("Frame log is append-only (Наредба Н-18 compliance).")
            )
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise UserError(
                _("Frame log is append-only (Наредба Н-18 compliance).")
            )
        return super().unlink()
