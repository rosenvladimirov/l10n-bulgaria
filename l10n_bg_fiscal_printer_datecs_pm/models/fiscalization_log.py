"""
l10n.bg.fp.frame.log — append-only frame audit trail.

Required by Наредба Н-18 (BG fiscalization). Stores the raw bytes of
every request and response between Odoo and the fiscal device. Records
are not deletable; not subject to GDPR erasure (fiscal records are exempt).
"""

from odoo import fields, models
from odoo.exceptions import UserError


class L10nBgFpFrameLog(models.Model):
    _name = "l10n.bg.fp.frame.log"
    _description = "Datecs Fiscal Printer Frame Log (append-only)"
    _order = "id desc"

    timestamp = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    device_id = fields.Many2one("l10n.bg.fp.device", index=True, required=True)
    receipt_id = fields.Many2one("l10n.bg.fp.receipt", index=True, ondelete="set null")

    direction = fields.Selection(
        [("out", "Host → Device"), ("in", "Device → Host")],
        required=True,
    )
    cmd = fields.Integer(string="Command")
    cmd_name = fields.Char()
    seq = fields.Integer(string="SEQ")

    raw_hex = fields.Char(string="Raw bytes (hex)")
    data_repr = fields.Char(string="DATA (repr)")
    status_hex = fields.Char(string="STATUS (hex)")
    error_code = fields.Integer()

    def write(self, vals):
        # Append-only — no edits except by superuser maintenance code.
        if not self.env.su:
            raise UserError(
                "Fiscal frame log is append-only (Наредба Н-18 compliance)."
            )
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise UserError(
                "Fiscal frame log is append-only (Наредба Н-18 compliance)."
            )
        return super().unlink()
