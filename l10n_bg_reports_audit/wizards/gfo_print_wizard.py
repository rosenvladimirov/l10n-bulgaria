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

    def _pl_compute_subtotals(self, values_expense, values_revenue):
        """Compute PL-specific subtotals not directly extractable from tags.

        Mutates the two dicts in-place to include:
          13000 Общо разходи     = 10000 + 11000
          18000 Общо приходи     = 15000 + 16000
          14100 Счет. печалба    = max(0, 18000 - 13000)
          19100 Счет. загуба     = max(0, 13000 - 18000)
          14000 Печалба от обич. = 15000 - 10000 + 16000 - 11000  (positive)
          19000 Загуба от обич.  = -above if negative
          14400 Г. Печалба       = 14100 - 14200 - 14300
          19200 Г. Загуба        = -(14400)  if 14400 < 0  else 0
          14500/19500 Всичко     = sum
        """
        total_exp_ops = sum(values_expense.get(c, 0.0) for c in ("10100", "10200", "10300", "10400", "10500"))
        total_exp_fin = sum(values_expense.get(c, 0.0) for c in ("11100", "11200"))
        total_rev_ops = sum(values_revenue.get(c, 0.0) for c in ("15100", "15200", "15300", "15400"))
        total_rev_fin = sum(values_revenue.get(c, 0.0) for c in ("16100", "16200", "16300"))

        values_expense["10000"] = total_exp_ops
        values_expense["11000"] = total_exp_fin
        values_expense["13000"] = total_exp_ops + total_exp_fin
        values_revenue["15000"] = total_rev_ops
        values_revenue["16000"] = total_rev_fin
        values_revenue["18000"] = total_rev_ops + total_rev_fin

        accounting_pl = values_revenue["18000"] - values_expense["13000"]
        values_expense["14100"] = max(0.0, accounting_pl)
        values_revenue["19100"] = max(0.0, -accounting_pl)

        ops_pl = (total_rev_ops - total_exp_ops) + (total_rev_fin - total_exp_fin)
        values_expense["14000"] = max(0.0, ops_pl)
        values_revenue["19000"] = max(0.0, -ops_pl)

        net_pl = (values_expense["14100"] - values_revenue["19100"]) - \
                 values_expense.get("14200", 0.0) - values_expense.get("14300", 0.0)
        values_expense["14400"] = max(0.0, net_pl)
        values_revenue["19200"] = max(0.0, -net_pl)

        values_expense["14500"] = values_expense["13000"] + \
                                   values_expense.get("14200", 0.0) + \
                                   values_expense.get("14300", 0.0) + \
                                   values_expense["14400"]
        values_revenue["19500"] = values_revenue["18000"] + values_revenue["19200"]

    def get_report_values(self):
        """Builder invoked from QWeb. Returns dict consumable by the template."""
        from odoo.addons.l10n_bg_reports_audit.data.gfo_balance_layout import (
            GFO_BALANCE_LAYOUT,
        )
        from odoo.addons.l10n_bg_reports_audit.data.gfo_pl_layout import (
            GFO_PL_LAYOUT,
        )

        self.ensure_one()
        values = self._gather_values(self.date_from, self.date_to, self.report_type)
        values_prev = None
        if self.show_previous_year:
            pf, pt = self._previous_year_bounds()
            values_prev = self._gather_values(pf, pt, self.report_type)

        if self.report_type == "gfo_balance":
            return {
                "wizard": self,
                "company": self.company_id,
                "asset_rows": self._build_rows(GFO_BALANCE_LAYOUT["asset"], values, values_prev),
                "liability_rows": self._build_rows(
                    GFO_BALANCE_LAYOUT["liability_equity"], values, values_prev,
                ),
                "show_previous": self.show_previous_year,
                "year_current": self.date_to.year,
                "year_previous": self.date_to.year - 1,
            }

        if self.report_type == "gfo_pl":
            # PL has two extract directions — split by position would be cleaner
            # but extract() returns both; we split here by code prefix:
            expense = {k: v for k, v in values.items() if k.startswith(("10", "11", "14"))}
            revenue = {k: v for k, v in values.items() if k.startswith(("15", "16", "18", "19"))}
            self._pl_compute_subtotals(expense, revenue)
            expense_prev = revenue_prev = None
            if values_prev:
                expense_prev = {k: v for k, v in values_prev.items() if k.startswith(("10", "11", "14"))}
                revenue_prev = {k: v for k, v in values_prev.items() if k.startswith(("15", "16", "18", "19"))}
                self._pl_compute_subtotals(expense_prev, revenue_prev)
            return {
                "wizard": self,
                "company": self.company_id,
                "expense_rows": self._build_rows(GFO_PL_LAYOUT["expense"], expense, expense_prev),
                "revenue_rows": self._build_rows(GFO_PL_LAYOUT["revenue"], revenue, revenue_prev),
                "show_previous": self.show_previous_year,
                "year_current": self.date_to.year,
                "year_previous": self.date_to.year - 1,
            }

        # CF/Equity/GOD — TODO Phase 4.3-4.5
        return {
            "wizard": self,
            "company": self.company_id,
            "rows": [],
            "show_previous": self.show_previous_year,
            "year_current": self.date_to.year,
            "year_previous": self.date_to.year - 1,
        }
