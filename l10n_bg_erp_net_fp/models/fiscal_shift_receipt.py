"""
l10n.bg.fiscal.shift.receipt — fiscal receipt 1:1 with device output.

These records are created by the OWL dashboard when the cashier
closes a shift — the browser pulls the device journal, parses it,
and ships a list of dicts via ORM call to `shift.action_mark_closed`.

Design choices:

* `pos.order` is NOT used. External-mode shops do NOT need Odoo POS
  reporting; they rely on the device's Z/EJ tape for fiscal records.
* `account.move` generation is opt-in (Phase 2) and runs as a separate
  reconcile pass — receipts can be persisted regardless of whether
  GL posting is configured.
* Lines are stored verbatim from the device payload — no PLU lookup
  is enforced on import (in case the registry has drifted since the
  shift opened).
"""

from odoo import _, fields, models


class L10nBgFiscalShiftReceipt(models.Model):
    _name = "l10n.bg.fiscal.shift.receipt"
    _description = "External-mode Fiscal Receipt"
    _order = "issued_at desc, id desc"
    _rec_name = "receipt_number"

    shift_id = fields.Many2one(
        "l10n.bg.fiscal.shift", required=True, ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(
        related="shift_id.company_id", store=True, index=True,
    )
    device_id = fields.Many2one(
        related="shift_id.device_id", store=True, index=True,
    )

    receipt_number = fields.Char(
        required=True, index=True,
        help="Unique sale number (UNS) reported by the device. Format: "
        "LLDDDDDD-CCCC-DDDDDDD on БГ devices.",
    )
    issued_at = fields.Datetime(required=True)

    total_amount = fields.Monetary(
        required=True, currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="shift_id.currency_id", store=True,
    )

    payment_kind = fields.Selection(
        [
            ("cash", "Cash"),
            ("card", "Card"),
            ("voucher", "Voucher"),
            ("mixed", "Mixed"),
            ("other", "Other"),
        ],
        index=True,
    )
    operator_code = fields.Char(
        help="Device operator slot (1..16 typically). Maps to a "
        "res.users record by `l10n_bg_fp_operator`.",
    )
    operator_user_id = fields.Many2one(
        "res.users",
        compute="_compute_operator_user", store=True, readonly=True,
    )

    line_ids = fields.One2many(
        "l10n.bg.fiscal.shift.receipt.line", "receipt_id",
    )
    raw_payload = fields.Text(
        help="Verbatim JSON from the device journal — preserved for "
        "audit purposes (Наредба Н-18).",
    )

    # Phase 2 — set on reconcile pass
    account_move_id = fields.Many2one(
        "account.move", readonly=True, copy=False,
    )

    _uniq_company_device_receipt = models.Constraint(
        "unique(company_id, device_id, receipt_number)",
        "Receipt number must be unique per device per company.",
    )

    def _compute_operator_user(self):
        Users = self.env["res.users"].sudo()
        for r in self:
            if not r.operator_code:
                r.operator_user_id = False
                continue
            r.operator_user_id = Users.search([
                ("l10n_bg_fp_operator", "=", r.operator_code),
                ("company_id", "in", (False, r.company_id.id)),
            ], limit=1)


class L10nBgFiscalShiftReceiptLine(models.Model):
    _name = "l10n.bg.fiscal.shift.receipt.line"
    _description = "External-mode Fiscal Receipt Line"
    _order = "receipt_id, sequence, id"

    receipt_id = fields.Many2one(
        "l10n.bg.fiscal.shift.receipt",
        required=True, ondelete="cascade", index=True,
    )
    sequence = fields.Integer(default=10)

    plu_number = fields.Integer(
        help="PLU slot on the device. Use to reverse-lookup the linked "
        "product(s) via `l10n.bg.fiscal.plu`.",
    )
    plu_id = fields.Many2one(
        "l10n.bg.fiscal.plu",
        compute="_compute_plu_id", store=True, readonly=True,
    )

    name = fields.Char(required=True)  # snapshot — what the device printed
    quantity = fields.Float(default=1.0, digits="Product Unit of Measure")
    unit_price = fields.Monetary(
        required=True, currency_field="currency_id",
    )
    line_total = fields.Monetary(
        required=True, currency_field="currency_id",
    )
    vat_letter = fields.Char(
        help="Device-side VAT letter (А/Б/В/Г). Use for ledger mapping.",
    )

    currency_id = fields.Many2one(
        related="receipt_id.currency_id", store=True,
    )

    @property
    def _company_field(self):
        return "receipt_id.company_id"

    def _compute_plu_id(self):
        Plu = self.env["l10n.bg.fiscal.plu"].sudo()
        for line in self:
            if not line.plu_number:
                line.plu_id = False
                continue
            company_id = line.receipt_id.company_id.id
            line.plu_id = Plu.search([
                ("plu_number", "=", line.plu_number),
                ("company_id", "=", company_id),
            ], limit=1)
