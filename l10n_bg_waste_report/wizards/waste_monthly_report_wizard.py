# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Wizard за месечна отчетна книга (Приложение №4)."""
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class WasteMonthlyReportWizard(models.TransientModel):
    _name = "l10n.bg.waste.monthly.report.wizard"
    _description = "Annex 4 - Monthly Waste Bookkeeping Wizard"

    site_id = fields.Many2one(
        "l10n.bg.waste.site",
        string="Site",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    period_year = fields.Integer(
        string="Year",
        required=True,
        default=lambda self: date.today().year,
    )
    period_month = fields.Selection(
        [(str(m), str(m)) for m in range(1, 13)],
        string="Month",
        required=True,
        default=lambda self: str(date.today().month),
    )
    waste_code_ids = fields.Many2many(
        "l10n.bg.waste.code",
        string="Restrict to Codes",
        domain="[('level','=','code')]",
        help="If empty, all codes attributed to the site for the period "
             "are included.",
    )
    recipient_partner_id = fields.Many2one(
        "res.partner",
        string="Send To (Consultant)",
        help="Optional. When set, the generated XLSX is emailed to this "
             "partner. Otherwise it is offered as a download only.",
    )

    @api.model
    def _date_range(self, year, month):
        """Връща (start_date, end_date_exclusive) за месеца."""
        start = date(year, int(month), 1)
        end = start + relativedelta(months=1)
        return start, end

    def action_generate(self):
        """Генерира XLSX отчета и (евент.) го изпраща."""
        self.ensure_one()
        start, end = self._date_range(self.period_year, self.period_month)
        data = {
            "site_id": self.site_id.id,
            "company_id": self.company_id.id,
            "date_from": fields.Date.to_string(start),
            "date_to": fields.Date.to_string(end),
            "waste_code_ids": self.waste_code_ids.ids,
            "recipient_partner_id": self.recipient_partner_id.id,
        }
        return self.env.ref(
            "l10n_bg_waste_report.action_report_waste_monthly_xlsx"
        ).report_action(self, data=data)
