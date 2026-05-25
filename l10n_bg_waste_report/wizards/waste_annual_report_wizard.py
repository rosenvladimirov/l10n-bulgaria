# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Wizard за годишен отчет (Приложение №18)."""
from datetime import date

from odoo import _, fields, models


class WasteAnnualReportWizard(models.TransientModel):
    _name = "l10n.bg.waste.annual.report.wizard"
    _description = "Annex 18 - Annual Waste Report Wizard"

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
        string="Reporting Year",
        required=True,
        default=lambda self: date.today().year - 1,
        help="The calendar year being reported on. The deadline for the "
             "Bulgarian regulator is March 10 of the following year.",
    )

    def action_generate(self):
        self.ensure_one()
        data = {
            "site_id": self.site_id.id,
            "company_id": self.company_id.id,
            "year": self.period_year,
        }
        return self.env.ref(
            "l10n_bg_waste_report.action_report_waste_annual_xlsx"
        ).report_action(self, data=data)
