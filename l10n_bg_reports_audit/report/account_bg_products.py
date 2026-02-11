# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from datetime import datetime, timedelta, date
from odoo import api, fields, models, tools
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import l10n_bg_where, \
    l10n_bg_get_account_deprecated_sql

_logger = logging.getLogger(__name__)


class AccountBGCalcProductLine(models.Model):
    """Base model for new Bulgarian Products trail balance reports."""

    _name = "account.bg.calc.product.line"
    _description = "Lines for Calculation Product Trail Balance in Bulgarian Localization"
    _auto = False
    _order = "move_id asc"

    company_id = fields.Many2one(
        "res.company", "Company", readonly=True, auto_join=True
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )

    move_id = fields.Many2one("account.move", string="Account Move", readonly=True)
    id = fields.Integer(string="ID", readonly=True, related="move_id.id")

    date = fields.Date(related="move_id.date", readonly=True)
    product_id = fields.Many2one("product.product", "Product", readonly=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
    )
    period = fields.Char(string="Period", readonly=True)
    account_type = fields.Selection(
        [
        ("asset_receivable", "Receivable"),
        ("liability_payable", "Payable"),
        ],
        readonly=True,
    )
    account_id = fields.Many2one(
        "account.account",
        "Account",
        readonly=True,
    )

    initial_balance_debit = fields.Monetary(
        string="Debit Initial Balance",
        currency_field="company_currency_id",
        readonly=True,
    )
    initial_balance_credit = fields.Monetary(
        string="Credit Initial Balance",
        currency_field="company_currency_id",
        readonly=True,
    )
    movement_balance_debit = fields.Monetary(
        string="Debit Movement",
        currency_field="company_currency_id",
        readonly=True,
    )
    movement_balance_credit = fields.Monetary(
        string="Credit Movement",
        currency_field="company_currency_id",
        readonly=True,
    )
    end_balance_debit = fields.Monetary(
        string="Debit End Balance",
        currency_field="company_currency_id",
        readonly=True,
    )
    end_balance_credit = fields.Monetary(
        string="Credit End Balance",
        currency_field="company_currency_id",
        readonly=True,
    )

    def open_journal_entry(self):
        self.ensure_one()
        return self.move_id.get_formview_action()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        _logger.debug(f"CREATE or REPLACE VIEW {self._table} as ({self._table_query})")
        self.env.cr.execute(
            sql.SQL(f"CREATE or REPLACE VIEW {self._table} as ({self._table_query})")
        )

    @property
    def _table_query(self):
        where_clauses = self._where()
        return f"""
        WITH RECURSIVE account_data AS (
            {self._select()}
        )
    SELECT
        company_id,
        id,
        move_id,
        product_id,
        account_id,
        state,
        date,
        period,
        account_type,
        SUM(CASE WHEN balance_type = 'initial' AND debit - credit > 0 THEN debit - credit ELSE 0 END) as initial_balance_debit,
        SUM(CASE WHEN balance_type = 'initial' AND debit - credit < 0 THEN credit - debit ELSE 0 END) as initial_balance_credit,
        SUM(CASE WHEN balance_type = 'movement' THEN debit ELSE 0 END) as movement_balance_debit,
        SUM(CASE WHEN balance_type = 'movement' THEN credit ELSE 0 END) as movement_balance_credit,
        SUM(CASE WHEN balance_type = 'final' AND debit - credit > 0 THEN debit - credit ELSE 0 END) as end_balance_debit,
        SUM(CASE WHEN balance_type = 'final' AND debit - credit < 0 THEN credit - debit ELSE 0 END) as end_balance_credit
    FROM account_data
    {'WHERE ' + where_clauses if where_clauses else ''}
    GROUP BY
    {self._group_by()}
    ORDER BY date
        """

    @api.model
    def _select(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, tax_periods, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            # Проверка дали date_from е първо число на годината
            first_day_of_year = date(date_from_obj.year, 1, 1)

            if date_from_obj != first_day_of_year:
                # Ако не е първо число - създаваме date_from_initial като предишния ден
                date_from_initial_obj = date_from_obj - timedelta(days=1)
            else:
                # Ако е първо число - използваме 31 декември на предходната година
                date_from_initial_obj = date(date_from_obj.year - 1, 12, 31)

            date_from_initial = f"'{date_from_initial_obj}'::date"
            date_from = f"'{date_from}'::date"
            date_to = f"'{date_to}'::date"
            company = f"AND aa.company_id = {company_id}"
        else:
            date_from_initial = "(date_trunc('year', CURRENT_DATE) - INTERVAL '1 day')"
            date_from = "date_trunc('year', CURRENT_DATE)"
            date_to = "CURRENT_DATE"
            company = ""
        deprecated = l10n_bg_get_account_deprecated_sql(table_alias='acc')

        return f"""
        /* Начално салдо */
        SELECT
            am.company_id,
            am.id,
            am.id AS move_id,
            aml.product_id,
            aml.account_id,
            am.state,
            am.date,
            to_char(am.date, 'YYYYMM') AS period,
            acc.account_type AS account_type,
            aml.debit,
            aml.credit,
            aml.balance,
            'initial' as balance_type
        FROM {self._from()}
        WHERE acc.reconcile = true
          AND {deprecated}
          {'AND ' + company if company else ''} AND am.date <= {date_from_initial}

        UNION ALL

        /* Движения */
        SELECT
            am.company_id,
            am.id,
            am.id AS move_id,
            aml.product_id,
            aml.account_id,
            am.state,
            am.date,
            to_char(am.date, 'YYYYMM') AS period,
            acc.account_type AS account_type,
            aml.debit,
            aml.credit,
            aml.balance,
            'movement' as balance_type
        FROM {self._from()}
        WHERE acc.reconcile = true
          AND {deprecated}
          {'AND ' + company if company else ''} AND am.date BETWEEN {date_from} AND {date_to}

        UNION ALL

        /* Краен баланс */
        SELECT
            am.company_id,
            am.id,
            am.id AS move_id,
            aml.product_id,
            aml.account_id,
            am.state,
            am.date,
            to_char(am.date, 'YYYYMM') AS period,
            acc.account_type AS account_type,
            aml.debit,
            aml.credit,
            aml.balance,
            'final' as balance_type
        FROM {self._from()}
        WHERE aml.product_id IS NOT NULL
          AND {deprecated}
          {'AND ' + company if company else ''} AND am.date <= {date_to}
        ORDER BY date  -- сортираме още в базовия SELECT
"""

    @api.model
    def _from(self):
        return """account_move_line AS aml
    LEFT JOIN account_move AS am
        ON aml.move_id = am.id
    INNER JOIN account_account AS acc
        ON aml.account_id = acc.id
    """

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            account_type = self._context.get("account_type")
            return f"""acc.account_type = '{account_type}'"""
        return """"""

    @api.model
    def _group_by(self):
        return """
        company_id,
        id,
        move_id,
        product_id,
        account_id,
        state,
        date,
        period,
        account_type
        """

