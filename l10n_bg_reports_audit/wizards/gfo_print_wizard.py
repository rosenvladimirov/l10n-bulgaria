#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""GFO/GOD Print Wizard — generates NSI-format PDFs from tag extractions.

Builds the hierarchy by combining:
  - layout dicts (data/gfo_*_layout.py) — section/group/leaf structure
  - l10n.bg.audit.extractor.extract() values — per leaf code

The wizard prepares a context dict that the QWeb template iterates.
"""
from datetime import date

from odoo import _, api, fields, models


class L10nBgGfoPrintWizard(models.TransientModel):
    _name = "l10n.bg.gfo.print.wizard"
    _description = "Print GFO / GOD NSI Annex 1 forms"

    report_type = fields.Selection(
        [
            ("gfo_balance", "Счетоводен баланс"),
            ("gfo_pl", "Отчет за приходите и разходите"),
            ("gfo_cf", "Отчет за паричните потоци (пряк метод)"),
            ("gfo_equity", "Отчет за собствения капитал"),
            ("god", "ГОД — Доп. справки"),
        ],
        default="gfo_balance",
        required=True,
    )
    date_from = fields.Date(
        required=True,
        default=lambda self: date(date.today().year - 1, 1, 1),
    )
    date_to = fields.Date(
        required=True,
        default=lambda self: date(date.today().year - 1, 12, 31),
    )
    show_previous_year = fields.Boolean(
        default=True,
        help="Render a second column with the previous year for comparison.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model
    def _build_rows(self, layout, values_current, values_previous=None):
        """Render a hierarchy → list of dicts for the QWeb template.

        Each output dict has:
          row_type, label, code, value, value_prev, indent (0/1/2/3)
        """
        rows = []
        for row_type, label, code, formula_codes in layout:
            indent = {
                "section": 0,
                "section_total": 0,
                "group": 1,
                "group_total": 1,
                "grand_total": 0,
                "leaf": 2,
                "leaf_sub": 3,
            }.get(row_type, 2)
            value = sum(values_current.get(c, 0.0) for c in (formula_codes or []))
            value_prev = (
                sum(values_previous.get(c, 0.0) for c in (formula_codes or []))
                if values_previous else None
            )
            rows.append({
                "row_type": row_type,
                "label": label,
                "code": code,
                "value": value,
                "value_prev": value_prev,
                "indent": indent,
                "is_bold": row_type in ("section", "section_total", "group_total", "grand_total"),
            })
        return rows

    def _gather_values(self, date_from, date_to, applicability_filter):
        """Return {nsi_code: signed_value} for the period."""
        extracted = self.env["l10n.bg.audit.extractor"].extract(
            applicability_filter, date_from, date_to, self.company_id.id,
        )
        result = {}
        for r in extracted:
            # tag_name format: "<NSI_CODE> — <label>"
            nsi_code = (r["tag_name"] or "").split(" — ")[0].strip()
            if nsi_code:
                result[nsi_code] = result.get(nsi_code, 0.0) + (r["value"] or 0.0)
        return result

    def _previous_year_bounds(self):
        prev_from = date(self.date_from.year - 1, self.date_from.month, self.date_from.day)
        prev_to = date(self.date_to.year - 1, self.date_to.month, self.date_to.day)
        return prev_from, prev_to

    def action_print(self):
        self.ensure_one()
        report_xmlid = {
            "gfo_balance": "l10n_bg_reports_audit.action_report_gfo_balance",
            "gfo_pl": "l10n_bg_reports_audit.action_report_gfo_pl",
            "gfo_cf": "l10n_bg_reports_audit.action_report_gfo_cf",
            "gfo_equity": "l10n_bg_reports_audit.action_report_gfo_equity",
            "god": "l10n_bg_reports_audit.action_report_god",
        }[self.report_type]
        return self.env.ref(report_xmlid).report_action(self)

    def get_report_values(self):
        """Builder invoked from QWeb. Returns dict consumable by the template."""
        from odoo.addons.l10n_bg_reports_audit.data.gfo_balance_layout import (
            GFO_BALANCE_LAYOUT,
        )

        self.ensure_one()
        values = self._gather_values(self.date_from, self.date_to, self.report_type)
        values_prev = None
        if self.show_previous_year:
            pf, pt = self._previous_year_bounds()
            values_prev = self._gather_values(pf, pt, self.report_type)

        if self.report_type == "gfo_balance":
            asset_rows = self._build_rows(
                GFO_BALANCE_LAYOUT["asset"], values, values_prev,
            )
            liability_rows = self._build_rows(
                GFO_BALANCE_LAYOUT["liability_equity"], values, values_prev,
            )
            return {
                "wizard": self,
                "company": self.company_id,
                "asset_rows": asset_rows,
                "liability_rows": liability_rows,
                "show_previous": self.show_previous_year,
                "year_current": self.date_to.year,
                "year_previous": self.date_to.year - 1,
            }
        # PL/CF/Equity/GOD — TODO: add layouts
        return {
            "wizard": self,
            "company": self.company_id,
            "rows": [],
            "show_previous": self.show_previous_year,
            "year_current": self.date_to.year,
            "year_previous": self.date_to.year - 1,
        }
