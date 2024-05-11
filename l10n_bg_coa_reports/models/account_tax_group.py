from odoo import fields, models


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_bg_vat_code = fields.Selection(
        [
            ("0", "0% VAT"),
            ("1", "9% VAT"),
            ("2", "20% VAT"),
        ],
        string="VAT Code",
        index=True,
        readonly=True,
    )
