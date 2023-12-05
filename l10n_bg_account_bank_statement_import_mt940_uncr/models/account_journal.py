#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        """Adds ofx to supported import formats."""
        rslt = super()._get_bank_statements_available_import_formats()
        rslt.append("mt940_uni_credit")
        return rslt
