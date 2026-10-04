# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import api, models

SALES_REPORT_DOCUMENT_TYPE = "81"


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        # Записът при затваряне на касова сесия (и сторното при фактура след
        # затворена сесия) е отчет за продажбите по чл. 119 ЗДДС: вид 81 и
        # случаен клиент. Партньорът влиза при СЪЗДАВАНЕТО — редовете взимат
        # партньора от записа (_compute_partner_id), а смяна след тях би
        # презаписала истинските клиенти по редовете на „Клиентска сметка“.
        journal_id = self.env.context.get("l10n_bg_pos_sales_report_journal")
        if journal_id:
            partner = self.env.ref(
                "l10n_bg_pos_sales_report.partner_random_customer", raise_if_not_found=False)
            for vals in vals_list:
                if vals.get("journal_id") != journal_id or vals.get("move_type", "entry") != "entry":
                    continue
                if partner and not vals.get("partner_id"):
                    vals["partner_id"] = partner.id
                vals.setdefault("l10n_bg_document_type", SALES_REPORT_DOCUMENT_TYPE)
        return super().create(vals_list)
