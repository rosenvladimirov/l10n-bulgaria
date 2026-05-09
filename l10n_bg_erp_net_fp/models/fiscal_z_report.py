"""
Per-session, per-device snapshot of a Z-report event.

Created at pos.session close-shift hook for every fiscal device on the
config. Stores the device's reported totals (when available) plus an
Odoo-aggregate pulled from the session's pos.order records so an
operator can see at a glance whether device and Odoo agree.

Reconcile semantics:

    matched           — device totals present and equal (within 0.01 BGN)
                        to Odoo aggregate per VAT group
    mismatch          — device totals present but differ from Odoo
                        aggregate; needs operator review
    no_device_totals  — driver did not return totals (e.g. Datecs ISL);
                        Odoo aggregate is recorded but cannot be
                        reconciled against the device
    error             — Z print attempt failed; raw_messages stored

Records are append-only — never deleted, never edited after create.
This is fiscal-grade audit trail.
"""
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class L10nBgFiscalZReport(models.Model):
    _name = "l10n.bg.fiscal.z.report"
    _description = "Bulgarian fiscal Z-report event (per session, per device)"
    _order = "create_date desc, id desc"

    name = fields.Char(
        compute="_compute_name", store=True, readonly=True,
    )
    session_id = fields.Many2one(
        "pos.session", required=True, ondelete="restrict", index=True,
    )
    device_id = fields.Many2one(
        "fiscal.printer.device", required=True, ondelete="restrict", index=True,
    )
    company_id = fields.Many2one(
        related="session_id.company_id", store=True, readonly=True,
    )

    report_number = fields.Integer(
        readonly=True,
        help="Sequential Z-report number reported by the device. "
             "Empty when the driver doesn't return it.",
    )
    z_print_at = fields.Datetime(
        default=fields.Datetime.now, readonly=True,
    )
    device_returned_totals = fields.Boolean(
        default=False, readonly=True,
    )

    # Per-group device totals — JSON-store keyed by group letter
    # ('А'..'З' in БГ Cyrillic, or 'A'..'H' from PM driver).
    device_totals_json = fields.Text(
        readonly=True,
        help="JSON: {group_letter: turnover_amount} as reported by the device.",
    )
    # Per-group Odoo aggregate computed from pos.order.line tax-group
    # mapping. Always populated regardless of device cooperation.
    odoo_totals_json = fields.Text(
        readonly=True,
        help="JSON: {group_letter: turnover_amount} aggregated from pos.order.",
    )

    reconcile_status = fields.Selection(
        [
            ("matched", "Matched"),
            ("mismatch", "Mismatch"),
            ("no_device_totals", "No device totals"),
            ("error", "Error"),
        ],
        default="no_device_totals",
        readonly=True,
        index=True,
    )
    reconcile_diff_json = fields.Text(
        readonly=True,
        help="JSON: per-group (device − Odoo) differences. "
             "Empty {} when matched.",
    )
    raw_messages = fields.Text(readonly=True)

    @api.depends("session_id", "device_id", "report_number")
    def _compute_name(self):
        for rec in self:
            sess = rec.session_id.name or "?"
            dev = rec.device_id.name or "?"
            num = rec.report_number or 0
            rec.name = f"Z #{num} · {dev} · {sess}"
