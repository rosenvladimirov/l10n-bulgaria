"""
account.move — fiscal action: print invoice on Datecs PM device.

Phase 1 entry point for back-office invoice printing. Wires `action_
l10n_bg_fp_datecs_print()` to a posted invoice → opens fiscal receipt,
registers each line as a sale, totals with cash payment, closes
receipt. UNS (NSale) is generated from the move.name + sequence.

NOTE: this is a minimal scaffold; the full implementation lands when
invoice_data (cmd 0x39, Phase 2) is in the facade.
"""

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_bg_fp_datecs_receipt_ids = fields.One2many(
        "l10n.bg.fp.receipt",
        compute="_compute_l10n_bg_fp_datecs_receipt_ids",
        string="Datecs PM Fiscal Receipts",
    )
    l10n_bg_fp_datecs_receipt_count = fields.Integer(
        compute="_compute_l10n_bg_fp_datecs_receipt_ids"
    )

    def _compute_l10n_bg_fp_datecs_receipt_ids(self):
        Receipt = self.env["l10n.bg.fp.receipt"]
        for move in self:
            recs = Receipt.search(
                [
                    ("res_model", "=", "account.move"),
                    ("res_id", "=", move.id),
                ]
            )
            move.l10n_bg_fp_datecs_receipt_ids = recs
            move.l10n_bg_fp_datecs_receipt_count = len(recs)

    def action_l10n_bg_fp_datecs_print(self):
        """Phase 1 stub — actual implementation requires Phase 2 (cmd 0x39
        invoice_data in the facade). Currently raises UserError to signal
        the gap explicitly to anyone wiring up the button.
        """
        self.ensure_one()
        raise UserError(
            _(
                "Datecs PM direct-print of invoices is on the Phase 2 roadmap. "
                "Until then, use l10n_bg_erp_net_fp for back-office invoice "
                "printing or wait for cmd 0x39 (invoice data) to land in the "
                "high-level facade."
            )
        )
