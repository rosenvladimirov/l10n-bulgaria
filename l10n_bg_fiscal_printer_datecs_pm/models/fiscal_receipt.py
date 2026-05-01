"""
l10n.bg.fp.receipt — record of one fiscal receipt printed by a Datecs
PM device.

Carries:
  * NSale (Unique Sale Number, basis of idempotent retry).
  * SlipNumber (returned by device on cmd 0x30 open).
  * Reference back to the Odoo source document (account.move, pos.order,
    sale.order, …) via res_model + res_id polymorphic link.

Schema is intentionally minimal in v18.0.1.0.0; SAF-T fields will be
added in a later phase.
"""

from odoo import fields, models


class L10nBgFpReceipt(models.Model):
    _name = "l10n.bg.fp.receipt"
    _description = "Datecs Fiscal Receipt"
    _order = "id desc"

    name = fields.Char(required=True, default="/")
    device_id = fields.Many2one(
        "l10n.bg.fp.device", required=True, ondelete="restrict"
    )
    session_id = fields.Many2one("l10n.bg.fp.session", ondelete="restrict")
    company_id = fields.Many2one(
        related="device_id.company_id", store=True, readonly=True
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Open"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
    )

    nsale = fields.Char(
        string="UNS / NSale",
        index=True,
        copy=False,
        help="Unique Sale Number (LLDDDDDD-CCCC-DDDDDDD). "
        "Identical NSales make `open_fiscal_receipt` idempotent.",
    )
    slip_number = fields.Integer(readonly=True, copy=False)
    is_invoice = fields.Boolean(default=False)

    opened_at = fields.Datetime()
    closed_at = fields.Datetime()

    total = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda s: s.env.company.currency_id,
    )

    res_model = fields.Char(string="Source Model", index=True)
    res_id = fields.Integer(string="Source ID", index=True)

    error_code = fields.Integer(readonly=True)
    error_message = fields.Char(readonly=True)

    log_ids = fields.One2many("l10n.bg.fp.frame.log", "receipt_id")
