"""
pos.order — fiscal receipt data persisted from a successful Datecs PM
print.

The fields are populated by the POS frontend (PaymentScreen patch)
after `validateOrder()` has successfully sent the receipt to the
device. They mirror the structure of `l10n_bg_erp_net_fp.pos_order`
to keep cross-module reporting consistent.

Reversal flow (PDF §4.6 cmd 0x2B): a refund order points to the
original via `refunded_order_ids`. The PaymentScreen patch picks up
the original's `*_receipt_number` / `*_uns` and submits a sibling
storno receipt; success populates the refund order's `is_reversal`
flag.
"""

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_bg_fp_datecs_receipt_number = fields.Char(
        string="Datecs Receipt #",
        readonly=True,
        copy=False,
        index=True,
        help="Slip number returned by the device on cmd 0x30 open / "
        "0x38 close.",
    )
    l10n_bg_fp_datecs_receipt_datetime = fields.Datetime(
        string="Datecs Receipt Date/Time",
        readonly=True,
        copy=False,
    )
    l10n_bg_fp_datecs_fm_number = fields.Char(
        string="Fiscal Memory #",
        readonly=True,
        copy=False,
        help="Fiscal memory serial number from cmd 0x7E sub-option 4.",
    )
    l10n_bg_fp_datecs_uns = fields.Char(
        string="Unique Sale # (UNS / NSale)",
        readonly=True,
        copy=False,
        index=True,
        help="LLDDDDDD-CCCC-DDDDDDD per PDF §10. Same UNS is used "
        "on a storno receipt to link it back to the original.",
    )
    l10n_bg_fp_datecs_is_fiscalized = fields.Boolean(
        string="Fiscalized?",
        readonly=True,
        copy=False,
    )
    l10n_bg_fp_datecs_is_reversal = fields.Boolean(
        string="Reversal?",
        readonly=True,
        copy=False,
    )
