# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _create_misc_reversal_move(self, payment_moves):
        # Фактура след затворена сесия: сторното на продажбата от отчета също
        # е част от отчета по чл. 119 — вид 81, случаен клиент
        order = self
        if self.company_id.country_id.code == "BG":
            order = self.with_context(l10n_bg_pos_sales_report_journal=self.config_id.journal_id.id)
        return super(PosOrder, order)._create_misc_reversal_move(payment_moves)
