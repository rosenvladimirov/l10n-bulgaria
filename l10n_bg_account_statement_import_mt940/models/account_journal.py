from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        """Adds mt940 to supported import formats."""
        rslt = super()._get_bank_statements_available_import_formats()
        rslt.append("mt940")
        return rslt
