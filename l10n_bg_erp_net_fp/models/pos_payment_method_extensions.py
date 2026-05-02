"""
Pinpad-aware payment method.

Marks a `pos.payment.method` as pinpad-driven so the POS UI knows to
delegate the charge to the local Python proxy (Odoo.ErpNet.FP) which
talks to a Datecs Pay (or compatible) pinpad through its proprietary
`libdatecs_pinpad.so`.

Strict ADD-only — no existing field, view or method is touched.
"""

from odoo import _, api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    l10n_bg_use_pinpad = fields.Boolean(
        string="Use Pinpad (proxy-driven)",
        default=False,
        help="When enabled, the POS will call the local Python proxy to "
        "perform the card charge on a physical pinpad before allowing the "
        "order to validate. Requires a fiscal device in proxy mode.",
    )
    l10n_bg_pinpad_id = fields.Char(
        string="Pinpad identifier",
        help="Identifier of the pinpad as registered in the Odoo.ErpNet.FP "
        "proxy `config.yaml` (e.g. `datecs_pay_main`). Optional — when "
        "blank the proxy chooses its default pinpad.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        # Add the two new fields to the data the POS browser receives,
        # so PaymentScreen can read them without an extra RPC.
        fields_list = super()._load_pos_data_fields(config)
        for f in ("l10n_bg_use_pinpad", "l10n_bg_pinpad_id"):
            if f not in fields_list:
                fields_list.append(f)
        return fields_list
