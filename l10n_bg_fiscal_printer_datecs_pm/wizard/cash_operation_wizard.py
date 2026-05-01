"""
Wizard for service cash in/out on a Datecs PM device.

Mirrors `l10n_bg_erp_net_fp.fiscal.cash.operation.wizard`. Opened from
the POS session form (action_l10n_bg_fp_datecs_cash_in/out), it wraps
cmd 0x46 with a confirmable form so the operator can enter amount and
reason.
"""

from odoo import _, fields, models
from odoo.exceptions import UserError


class CashOperationWizard(models.TransientModel):
    _name = "l10n.bg.fp.datecs.cash.operation.wizard"
    _description = "Datecs PM cash in/out"

    session_id = fields.Many2one(
        "pos.session",
        string="POS Session",
        required=True,
        ondelete="cascade",
    )
    device_id = fields.Many2one(
        "l10n.bg.fp.device",
        related="session_id.l10n_bg_fp_datecs_device_id",
        readonly=True,
    )
    operation_type = fields.Selection(
        [("in", "Cash in (служебно въведено)"),
         ("out", "Cash out (служебно изведено)")],
        required=True,
    )
    amount = fields.Float(required=True)
    reason = fields.Char()

    def action_execute(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Amount must be positive."))
        if not self.device_id:
            raise UserError(
                _("This POS session is not linked to a Datecs PM device.")
            )
        try:
            if self.operation_type == "in":
                safe, _ti, _to = self.device_id.cash_in(
                    self.amount, reason=self.reason or ""
                )
                title = _("Cash in")
            else:
                safe, _ti, _to = self.device_id.cash_out(
                    self.amount, reason=self.reason or ""
                )
                title = _("Cash out")
        except Exception as exc:
            raise UserError(
                _(
                    "Cash operation failed: %(err)s",
                    err=str(exc),
                )
            ) from exc

        self.session_id.message_post(
            body=_(
                "%(title)s: %(amt).2f (%(reason)s) — safe %(safe).2f",
                title=title,
                amt=self.amount,
                reason=self.reason or _("no reason"),
                safe=safe,
            ),
            message_type="notification",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": _(
                    "%(amt).2f processed. Cash in safe: %(safe).2f.",
                    amt=self.amount,
                    safe=safe,
                ),
                "type": "success",
            },
        }
