"""
l10n.bg.fp.session — fiscal session = Z-cycle on the Datecs device.

This is NOT the same as `pos.session` (the browser/UI shift). A
fiscal session represents the period between two Z-reports on the
fiscal device, which is enforced by Наредба Н-18 (≤ 24h). It can be
triggered from a `pos.session` opening, from a back-office bulk-print
job, or manually by an administrator — `source` records which.

A `pos.session` may span multiple fiscal sessions (long shift across
midnight Z) and a fiscal session may outlive a `pos.session` (Z taken
later by a cron). They are linked via `pos_session_id` when relevant
but never identified.
"""

from odoo import api, fields, models


class L10nBgFpSession(models.Model):
    _name = "l10n.bg.fp.session"
    _description = "Datecs Fiscal Session (Z-cycle)"
    _order = "id desc"

    name = fields.Char(required=True, default="/")
    device_id = fields.Many2one(
        "l10n.bg.fp.device", required=True, ondelete="restrict"
    )
    company_id = fields.Many2one(
        related="device_id.company_id", store=True, readonly=True
    )

    state = fields.Selection(
        [("open", "Open"), ("closed", "Closed (Z reported)")],
        default="open",
        required=True,
    )
    opened_at = fields.Datetime(default=fields.Datetime.now)
    closed_at = fields.Datetime()

    # ---- "what kind of fiscal session is this" --------------------------
    source = fields.Selection(
        [
            ("pos_external", "POS — external mode (КА като POS)"),
            ("pos_printer", "POS — printer mode (Odoo POS + receipt printer)"),
            ("backend", "Back-office (invoicing)"),
            ("manual", "Manual (admin button)"),
            ("cron", "Scheduled cron"),
        ],
        required=True,
        default="manual",
        help="Marks how this fiscal session was started — clearly "
        "separates POS-driven sessions from back-office and manual ones.",
    )
    is_pos_driven = fields.Boolean(
        compute="_compute_is_pos_driven", store=True, index=True
    )
    pos_session_id = fields.Many2one(
        "pos.session",
        string="POS UI Session",
        ondelete="set null",
        index=True,
        help="Back-link to the browser/UI POS session that triggered "
        "this fiscal session, if any. The two are NOT the same — "
        "fiscal sessions live on the device, POS sessions in the "
        "Odoo UI; their lifecycles can differ.",
    )

    receipt_count = fields.Integer(compute="_compute_receipt_count")
    receipt_ids = fields.One2many("l10n.bg.fp.receipt", "session_id")

    z_report_number = fields.Integer(string="Z Report #", readonly=True)

    def _compute_receipt_count(self):
        for rec in self:
            rec.receipt_count = len(rec.receipt_ids)

    @api.depends("source")
    def _compute_is_pos_driven(self):
        for rec in self:
            rec.is_pos_driven = rec.source in ("pos_external", "pos_printer")
