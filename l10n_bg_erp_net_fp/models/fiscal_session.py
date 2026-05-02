"""
Fiscal session = Z-cycle on the fiscal device.

Distinct from `pos.session` (the browser/UI shift): a fiscal session
represents the period between two Z-reports on the **device**, which
Наредба Н-18 limits to ≤ 24 hours. A pos.session may span multiple
fiscal sessions (long shift across midnight Z) and a fiscal session
may outlive a pos.session (Z taken later by cron). They are linked via
`pos_session_id` when relevant but never identified.

This is a NEW model; it adds no requirements on existing addon logic.
"""

from odoo import api, fields, models


SESSION_SOURCE = [
    ("pos_external", "POS — external mode (КА като POS)"),
    ("pos_printer", "POS — printer mode (Odoo POS + receipt printer)"),
    ("backend", "Back-office (invoicing)"),
    ("manual", "Manual (admin button)"),
    ("cron", "Scheduled cron"),
]


class FiscalSession(models.Model):
    _name = "fiscal.session"
    _description = "Fiscal Session (Z-cycle marker)"
    _order = "id desc"

    name = fields.Char(default="/", required=True)
    device_id = fields.Many2one(
        "fiscal.printer.device",
        required=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    state = fields.Selection(
        [("open", "Open"), ("closed", "Closed (Z reported)")],
        default="open",
        required=True,
    )
    opened_at = fields.Datetime(default=fields.Datetime.now)
    closed_at = fields.Datetime()
    z_report_number = fields.Integer(
        string="Z report #",
        readonly=True,
    )

    source = fields.Selection(
        SESSION_SOURCE,
        required=True,
        default="manual",
        help="What triggered this fiscal session — POS open, "
        "back-office bulk print, manual admin button, or scheduled cron.",
    )
    is_pos_driven = fields.Boolean(
        compute="_compute_is_pos_driven",
        store=True,
        index=True,
    )
    pos_session_id = fields.Many2one(
        "pos.session",
        ondelete="set null",
        index=True,
        help="Back-link to the browser/UI POS session that triggered "
        "this fiscal session, if any. The two are NOT the same — "
        "fiscal sessions live on the device, POS sessions in the "
        "Odoo UI; their lifecycles can differ.",
    )

    receipt_count = fields.Integer(compute="_compute_receipt_count")

    @api.depends("source")
    def _compute_is_pos_driven(self):
        for rec in self:
            rec.is_pos_driven = rec.source in ("pos_external", "pos_printer")

    def _compute_receipt_count(self):
        # Count pos.order lines linked through pos_session_id when set;
        # otherwise zero (no direct receipt link in this model).
        for rec in self:
            if rec.pos_session_id:
                rec.receipt_count = self.env["pos.order"].search_count(
                    [("session_id", "=", rec.pos_session_id.id)]
                )
            else:
                rec.receipt_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "/":
                next_name = seq.next_by_code("fiscal.session.sequence")
                if next_name:
                    vals["name"] = next_name
        return super().create(vals_list)

    def action_close(self):
        """Mark the fiscal session as closed (after Z report fired).
        Doesn't fire the Z itself — that's a separate device action.
        """
        self.write({
            "state": "closed",
            "closed_at": fields.Datetime.now(),
        })
