"""
Per-cashier fiscal-printer operator credentials.

Bulgarian fiscal printers (Datecs PM/ISL, Daisy, Eltrade, Tremol, ...)
authenticate every receipt with an operator number (1..30 typically)
and a 4-digit password. Defaults from the factory are operator=1 and
password=0000; some merchants assign one number per cashier so the
device's audit log attributes each receipt to the right person.

These two fields live on `res.users` so they follow the cashier
across POS configs / sessions. They are sent in every fiscal-receipt
request from the POS frontend (see `static/src/js/erp_net_fp_printer.js`)
and used by backend flows (X / Z reports, cash withdraw / deposit,
PLU sync) when the calling user has them set.

If the field is empty, the ErpNet.FP server falls back to the
`operator` / `operator_password` keys configured in its `config.yaml`
for the targeted printer.
"""

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    l10n_bg_fp_operator = fields.Char(
        string="Fiscal printer operator code",
        size=2,
        help="Operator number on the Bulgarian fiscal printer "
             "(typically 1..30). Sent in every fiscal-receipt and "
             "report request issued by this user. Leave empty to "
             "fall back to the ErpNet.FP server default (operator=1).",
    )
    l10n_bg_fp_operator_password = fields.Char(
        string="Fiscal printer operator password",
        size=8,
        help="Password for this operator on the Bulgarian fiscal "
             "printer. Default factory value is `0000` (Datecs / "
             "Daisy / Eltrade / Tremol all ship with this). Leave "
             "empty to fall back to the ErpNet.FP server default.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        # Allow the user to see their own operator code/password on
        # the "My Profile" page (without admin rights).
        return super().SELF_READABLE_FIELDS + [
            "l10n_bg_fp_operator",
            "l10n_bg_fp_operator_password",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        # And edit them themselves — admin still doesn't need to be
        # involved for cashiers to enter their device password.
        return super().SELF_WRITEABLE_FIELDS + [
            "l10n_bg_fp_operator",
            "l10n_bg_fp_operator_password",
        ]
