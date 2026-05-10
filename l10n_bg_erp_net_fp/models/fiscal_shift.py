"""
l10n.bg.fiscal.shift — independent shift record for external POS mode.

Decoupled from `pos.session` — the cashier rings up sales DIRECTLY on
the fiscal device (PLU keypad / barcode scanner); Odoo plays the role
of shift container + monitor only. Browser-mediated proxy fetches do
all device I/O (server has no LAN reachability into the merchant's
private network).

The shift state machine:

    draft → opening → open → closing → closed
                ↓                ↓
              error            error

A shift wraps zero-or-more fiscal receipts pulled from the device's
journal at close time. There is NO `pos.order` create — the receipt
records are first-class citizens (`l10n.bg.fiscal.shift.receipt`).
"""

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nBgFiscalShift(models.Model):
    _name = "l10n.bg.fiscal.shift"
    _description = "External-mode Fiscal Shift"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        required=True, copy=False, default="/", index=True, readonly=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, index=True,
        default=lambda self: self.env.company,
    )
    device_id = fields.Many2one(
        "fiscal.printer.device",
        required=True,
        ondelete="restrict",
        domain="[('company_id','in',(False, company_id))]"
        if False else "[]",  # placeholder — device has no company_id field
        help="Fiscal device this shift drives. PLU/VAT/operators are pushed "
        "to this device on open; Z-report and journal are pulled on close.",
    )
    operator_user_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        help="Cashier responsible for this shift. Their "
        "`l10n_bg_fp_operator` code is pushed to the device on open.",
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("opening", "Opening (push PLU/VAT/operator)"),
            ("open", "Open"),
            ("closing", "Closing (Z + import)"),
            ("closed", "Closed"),
            ("error", "Error"),
        ],
        default="draft",
        tracking=True,
        index=True,
        copy=False,
    )

    opened_at = fields.Datetime(readonly=True, copy=False)
    closed_at = fields.Datetime(readonly=True, copy=False)

    # Z-report payload after close
    z_number = fields.Integer(readonly=True, copy=False)
    z_total = fields.Monetary(
        readonly=True, copy=False, currency_field="currency_id",
    )
    z_payload_json = fields.Text(readonly=True, copy=False)

    currency_id = fields.Many2one(
        related="company_id.currency_id", store=True, readonly=True,
    )

    push_summary = fields.Text(
        readonly=True, copy=False,
        help="Multi-line summary of what was pushed at open / pulled at "
        "close. Each line: `[step] ✓|✗ message`.",
    )

    # Receipts pulled from device journal at close
    receipt_ids = fields.One2many(
        "l10n.bg.fiscal.shift.receipt", "shift_id",
    )
    receipt_count = fields.Integer(
        compute="_compute_receipt_stats", store=True,
    )
    sales_total = fields.Monetary(
        compute="_compute_receipt_stats", store=True,
        currency_field="currency_id",
    )

    @api.depends("receipt_ids", "receipt_ids.total_amount")
    def _compute_receipt_stats(self):
        for shift in self:
            shift.receipt_count = len(shift.receipt_ids)
            shift.sales_total = sum(shift.receipt_ids.mapped("total_amount"))

    # ------------------------------------------------------------------
    # Lifecycle helpers — called from the OWL dashboard via ORM RPC.
    # The actual device I/O happens in the browser; these methods only
    # mutate the DB record.
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "l10n.bg.fiscal.shift") or "/"
        return super().create(vals_list)

    def action_mark_opening(self):
        """Browser is about to push PLU/VAT/operators — set state."""
        self.ensure_one()
        if self.state not in ("draft", "error"):
            raise UserError(_(
                "Shift cannot move to 'opening' from state %s.") % self.state)
        self.write({"state": "opening"})

    def action_mark_open(self, push_summary=""):
        """Browser successfully pushed config — shift is now live."""
        self.ensure_one()
        if self.state not in ("opening",):
            raise UserError(_(
                "Shift cannot move to 'open' from state %s.") % self.state)
        self.write({
            "state": "open",
            "opened_at": fields.Datetime.now(),
            "push_summary": push_summary,
        })

    def action_mark_closing(self):
        """Browser is about to fire Z + pull journal."""
        self.ensure_one()
        if self.state not in ("open", "error"):
            raise UserError(_(
                "Shift cannot move to 'closing' from state %s.") % self.state)
        self.write({"state": "closing"})

    def action_mark_closed(self, z_data=None, receipts_data=None,
                            push_summary=""):
        """Browser delivered Z + journal — persist and close.

        :param z_data: dict {z_number, total, payload}
        :param receipts_data: list of dicts matching the
            l10n.bg.fiscal.shift.receipt create() payload.
        """
        self.ensure_one()
        if self.state not in ("closing",):
            raise UserError(_(
                "Shift cannot move to 'closed' from state %s.") % self.state)
        z = z_data or {}
        if receipts_data:
            for r in receipts_data:
                r.setdefault("shift_id", self.id)
            self.env["l10n.bg.fiscal.shift.receipt"].sudo().create(
                receipts_data)
        self.write({
            "state": "closed",
            "closed_at": fields.Datetime.now(),
            "z_number": z.get("z_number") or 0,
            "z_total": z.get("total") or 0.0,
            "z_payload_json": json.dumps(z, ensure_ascii=False) if z else False,
            "push_summary": (
                (self.push_summary or "") + "\n--- close ---\n" + push_summary
                if self.push_summary else push_summary
            ),
        })

    def action_mark_error(self, message=""):
        """Browser hit a fatal device error — surface it."""
        self.ensure_one()
        self.write({
            "state": "error",
            "push_summary": (self.push_summary or "") + "\n[error] " + message,
        })

    # ------------------------------------------------------------------
    # Convenience — find current open shift for a device (used by OWL
    # dashboard at load time).
    # ------------------------------------------------------------------

    @api.model
    def find_active_shift(self, device_id):
        """Return the currently-open shift on a device, or False."""
        return self.search([
            ("device_id", "=", device_id),
            ("state", "in", ("opening", "open", "closing")),
        ], limit=1)
