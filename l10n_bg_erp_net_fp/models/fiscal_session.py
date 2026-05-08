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
    _inherit = ["mail.thread", "mail.activity.mixin"]
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
        [
            ("open", "Open"),
            ("closed", "Closed (Z reported)"),
            ("closed_partial", "Closed (force / no Z)"),
        ],
        default="open",
        required=True,
    )
    opened_at = fields.Datetime(default=fields.Datetime.now)
    closed_at = fields.Datetime()
    z_report_number = fields.Integer(
        string="Z report #",
        readonly=True,
    )
    z_total_amount = fields.Monetary(
        string="Z total",
        readonly=True,
        currency_field="currency_id",
        help="Total turnover reported on the Z-report.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
        store=True,
    )
    imported_receipt_count = fields.Integer(
        readonly=True,
        help="Number of fiscal receipts imported from the device on close.",
    )
    discrepancy = fields.Monetary(
        string="Discrepancy (Odoo vs Z)",
        readonly=True,
        currency_field="currency_id",
        help="Difference between sum of imported pos.order amounts and "
        "the Z-report total. Non-zero = receipts may be missing or "
        "duplicated; investigate.",
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

    # ------------------------------------------------------------------
    # Cron auto-close — Наредба Н-18 caps fiscal sessions at 24h
    # ------------------------------------------------------------------

    @api.model
    def _cron_auto_close_stuck_sessions(self):
        """Find fiscal.session records that have been open longer than
        the configured threshold (default 23h to leave headroom before
        the 24h Н-18 limit) and try to close them.

        Strategy:
          - If the fiscal.session has a linked pos.session that's still
            open in external mode, run the close orchestrator (which
            pulls sales, imports, runs Z, closes both).
          - If the fiscal.session is orphan (no pos.session), just
            trigger Z directly and mark closed_partial — manual
            reconcile required.

        Failures are logged + a mail.activity is created on the
        device's manager so someone investigates next morning.
        """
        from datetime import timedelta
        threshold = fields.Datetime.now() - timedelta(hours=23)
        stuck = self.search([
            ("state", "=", "open"),
            ("opened_at", "<", threshold),
        ])
        if not stuck:
            return True

        from odoo.tools import logging as _logging  # noqa: F401
        import logging
        _logger = logging.getLogger(__name__)

        for fsess in stuck:
            try:
                # Path A — linked pos.session, run close orchestrator
                pos_sess = fsess.pos_session_id
                if pos_sess and pos_sess.state == "opened":
                    _logger.info(
                        "Auto-closing stuck fiscal.session %s via pos.session %s",
                        fsess.name, pos_sess.name,
                    )
                    pos_sess._l10n_bg_external_close_orchestrate()
                    continue

                # Path B — orphan (or pos.session already closed):
                # trigger Z directly + mark closed_partial
                _logger.info(
                    "Auto-closing orphan fiscal.session %s via direct Z",
                    fsess.name,
                )
                z = fsess.device_id._l10n_bg_print_z()
                if z["ok"]:
                    fsess.write({
                        "state": "closed",
                        "closed_at": fields.Datetime.now(),
                        "z_report_number": z["z_number"],
                        "z_total_amount": z["total"],
                    })
                else:
                    fsess.write({
                        "state": "closed_partial",
                        "closed_at": fields.Datetime.now(),
                    })
                    fsess._l10n_bg_post_alert(
                        "Auto-Z failed: %s" % z["message"]
                    )
            except Exception as exc:  # noqa: BLE001
                _logger.exception(
                    "Auto-close failed for fiscal.session %s", fsess.name
                )
                fsess._l10n_bg_post_alert(
                    "Auto-close exception: %s" % str(exc)[:300]
                )

        return True

    def _l10n_bg_post_alert(self, message):
        """Post a mail.activity on the device record so the responsible
        manager sees the issue at start-of-day. Uses the standard
        ``mail.activity`` mechanism (already a dep of l10n_bg_erp_net_fp).
        """
        self.ensure_one()
        try:
            self.device_id.activity_schedule(
                act_type_xmlid="mail.mail_activity_data_warning",
                summary="Fiscal session auto-close issue",
                note=message,
                user_id=(
                    self.device_id.responsible_user_id.id
                    if "responsible_user_id" in self.device_id._fields
                    and self.device_id.responsible_user_id
                    else self.env.uid
                ),
            )
        except Exception:  # noqa: BLE001
            # mail.activity_data_warning may not exist on all installs.
            # Fall back to a chatter message on the fiscal.session itself.
            if hasattr(self, "message_post"):
                self.message_post(body=message)
