# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""SQL view models for Bulgarian Annual Reports — one row per (tag, account)
aggregation, filtered by `account.account.tag.l10n_bg_applicability`.

Five views, one per report category:
    - account.bg.gfo.balance.line   (l10n_bg_applicability = gfo_balance)
    - account.bg.gfo.pl.line        (l10n_bg_applicability = gfo_pl)
    - account.bg.gfo.cf.line        (l10n_bg_applicability = gfo_cf)
    - account.bg.gfo.equity.line    (l10n_bg_applicability = gfo_equity)
    - account.bg.god.line           (l10n_bg_applicability = god)

Each row carries the per-tag, per-account aggregated debit/credit/balance plus
the signed `value` (already applies the `l10n_bg_position` formula).
"""
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    l10n_bg_where,
    l10n_bg_get_account_deprecated_sql,
)

_logger = logging.getLogger(__name__)


class L10nBgAnnualLineMixin(models.AbstractModel):
    """Common columns + SQL builder for annual report SQL views."""

    _name = "l10n.bg.annual.line.mixin"
    _description = "BG Annual Report Line — Common SQL Builder"

    # Overridden by concrete models. Drives the SQL WHERE clause:
    #   WHERE aat.l10n_bg_applicability = '<APPLICABILITY>'
    _L10N_BG_APPLICABILITY = None

    company_id = fields.Many2one("res.company", "Company", readonly=True, auto_join=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )
    account_id = fields.Many2one("account.account", "Account", readonly=True)
    account_code = fields.Char("Account Code", readonly=True)
    account_name = fields.Char("Account Name", readonly=True)
    account_type = fields.Char("Account Type", readonly=True)
    tag_id = fields.Many2one("account.account.tag", "Report Tag", readonly=True)
    tag_name = fields.Char("Tag Name", readonly=True)
    l10n_bg_position = fields.Char("Report Position", readonly=True)
    l10n_bg_extract_basis = fields.Char("Extraction Basis", readonly=True)
    period = fields.Char("Period", readonly=True)
    debit_sum = fields.Monetary(
        "Debit", currency_field="company_currency_id", readonly=True
    )
    credit_sum = fields.Monetary(
        "Credit", currency_field="company_currency_id", readonly=True
    )
    balance_sum = fields.Monetary(
        "Balance", currency_field="company_currency_id", readonly=True
    )
    value = fields.Monetary(
        "Signed Value", currency_field="company_currency_id", readonly=True,
        help="Signed value computed from l10n_bg_position formula."
    )

    @api.model
    def _l10n_bg_period_bounds(self):
        """Resolve (date_from, date_to, company_id) — from report_options
        context if present, otherwise fall back to current fiscal year."""
        if self._context.get("report_options"):
            date_from, date_to, _tp, _tps, company_id, _state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            return (
                f"'{date_from}'::date",
                f"'{date_to}'::date",
                company_id,
            )
        return (
            "date_trunc('year', CURRENT_DATE)::date",
            "CURRENT_DATE::date",
            self.env.company.id,
        )

    @api.model
    def _select(self):
        return """
            row_number() OVER () AS id,
            aml.company_id,
            aml.account_id,
            COALESCE(
                aa.code_store::jsonb ->> aml.company_id::text,
                aa.code_store::text
            ) AS account_code,
            aa.name AS account_name,
            aa.account_type::text AS account_type,
            aat.id AS tag_id,
            aat.name AS tag_name,
            aat.l10n_bg_position::text AS l10n_bg_position,
            aat.l10n_bg_extract_basis::text AS l10n_bg_extract_basis,
            to_char(MIN(aml.date), 'YYYYMM') AS period,
            SUM(aml.debit) AS debit_sum,
            SUM(aml.credit) AS credit_sum,
            SUM(aml.balance) AS balance_sum,
            CASE
                WHEN aat.l10n_bg_position = 'asset' THEN SUM(aml.balance)
                WHEN aat.l10n_bg_position = 'liability_equity' THEN -SUM(aml.balance)
                WHEN aat.l10n_bg_position = 'revenue' THEN SUM(aml.credit) - SUM(aml.debit)
                WHEN aat.l10n_bg_position = 'expense' THEN SUM(aml.debit) - SUM(aml.credit)
                WHEN aat.l10n_bg_position = 'inflow' THEN SUM(aml.credit) - SUM(aml.debit)
                WHEN aat.l10n_bg_position = 'outflow' THEN SUM(aml.debit) - SUM(aml.credit)
                WHEN aat.l10n_bg_position = 'increase' THEN ABS(SUM(aml.balance))
                WHEN aat.l10n_bg_position = 'decrease' THEN -ABS(SUM(aml.balance))
                ELSE 0
            END AS value
        """

    @api.model
    def _from(self):
        return """
            account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            JOIN l10n_bg_aml_account_tag_rel rel
                ON rel.aml_id = aml.id
            JOIN account_account_tag aat
                ON aat.id = rel.tag_id
        """

    @api.model
    def _where(self):
        date_from, date_to, company_id = self._l10n_bg_period_bounds()
        deprecated = l10n_bg_get_account_deprecated_sql(table_alias="aa")
        return f"""
            aat.l10n_bg_applicability = '{self._L10N_BG_APPLICABILITY}'
            AND aat.l10n_bg_position IS NOT NULL
            AND am.state = 'posted'
            AND aml.company_id = {company_id}
            AND {deprecated}
            AND (
                (aat.l10n_bg_extract_basis = 'balance' AND aml.date <= {date_to})
                OR
                (aat.l10n_bg_extract_basis = 'turnover'
                 AND aml.date >= {date_from}
                 AND aml.date <= {date_to})
            )
        """

    @api.model
    def _group_by(self):
        return """
            aml.company_id, aml.account_id, aa.id, aa.code_store, aa.name, aa.account_type,
            aat.id, aat.name, aat.l10n_bg_position, aat.l10n_bg_extract_basis
        """

    @property
    def _table_query(self):
        return f"""
            SELECT {self._select()}
            FROM {self._from()}
            WHERE {self._where()}
            GROUP BY {self._group_by()}
        """

    def init(self):
        if self._L10N_BG_APPLICABILITY is None:
            return
        tools.drop_view_if_exists(self.env.cr, self._table)
        _logger.debug("CREATE VIEW %s AS %s", self._table, self._table_query)
        self.env.cr.execute(
            sql.SQL(f"CREATE or REPLACE VIEW {self._table} AS ({self._table_query})")
        )


class AccountBgGfoBalanceLine(models.Model):
    _name = "account.bg.gfo.balance.line"
    _inherit = "l10n.bg.annual.line.mixin"
    _description = "BG GFO Balance Sheet — Per (Tag, Account)"
    _auto = False
    _order = "account_code asc, tag_name asc"
    _L10N_BG_APPLICABILITY = "gfo_balance"


class AccountBgGfoPlLine(models.Model):
    _name = "account.bg.gfo.pl.line"
    _inherit = "l10n.bg.annual.line.mixin"
    _description = "BG GFO Profit & Loss — Per (Tag, Account)"
    _auto = False
    _order = "account_code asc, tag_name asc"
    _L10N_BG_APPLICABILITY = "gfo_pl"


class AccountBgGfoCfLine(models.Model):
    _name = "account.bg.gfo.cf.line"
    _inherit = "l10n.bg.annual.line.mixin"
    _description = "BG GFO Cash Flow — Per (Tag, Account)"
    _auto = False
    _order = "account_code asc, tag_name asc"
    _L10N_BG_APPLICABILITY = "gfo_cf"


class AccountBgGfoEquityLine(models.Model):
    _name = "account.bg.gfo.equity.line"
    _inherit = "l10n.bg.annual.line.mixin"
    _description = "BG GFO Changes in Equity — Per (Tag, Account)"
    _auto = False
    _order = "account_code asc, tag_name asc"
    _L10N_BG_APPLICABILITY = "gfo_equity"


class AccountBgGodLine(models.Model):
    _name = "account.bg.god.line"
    _inherit = "l10n.bg.annual.line.mixin"
    _description = "BG NSI Annual Activity Report — Per (Tag, Account)"
    _auto = False
    _order = "account_code asc, tag_name asc"
    _L10N_BG_APPLICABILITY = "god"
