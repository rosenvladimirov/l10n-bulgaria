# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        session = self
        if self.company_id.country_id.code == "BG":
            session = self.with_context(l10n_bg_pos_sales_report_journal=self.config_id.journal_id.id)
        return super(PosSession, session)._create_account_move(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs,
        )
