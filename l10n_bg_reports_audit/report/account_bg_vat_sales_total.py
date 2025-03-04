# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    l10n_bg_odoo_compatible,
    l10n_bg_where,
)

_logger = logging.getLogger(__name__)


class AccountBGTotalSalesLine(models.Model):
    """Base model for new Bulgarian VAT reports."""

    _name = "account.bg.total.sales.line"
    _description = "VAT line for Analysis in Bulgarian Localization"
    _auto = False
    _rec_name = "move_id"
    _order = "company_id asc"

    move_id = fields.Integer(string="Total", readonly=True)
    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )
    info_tag_3 = fields.Char(string="[02-03] Tax period", readonly=True)
    info_tag_5 = fields.Integer(string="[02-05] Counter sales", readonly=True)
    info_tag_6 = fields.Integer(string="[02-06] Counter purchases", readonly=True)
    account_tag_10 = fields.Monetary(
        string="[02-10] Total amount of base",
        currency_field="company_currency_id",
        readonly=True,
        help="Total amount of base",
    )
    account_tag_20 = fields.Monetary(
        string="[02-20] Total VAT", currency_field="company_currency_id", readonly=True
    )
    account_tag_11 = fields.Monetary(
        string="[02-11] Base for domestic taxation (20%)",
        currency_field="company_currency_id",
        readonly=True,
        help="Base amount from sales for domestic taxation (20%)",
    )
    account_tag_12 = fields.Monetary(
        string="[02-12] Base for ICA",
        currency_field="company_currency_id",
        readonly=True,
        help="Base amount for ICD and tax basis "
        "of received supplies under Art. 82, para. 2 - 5 VAT",
    )
    account_tag_13 = fields.Monetary(
        string="[02-13] Base travel services 9%",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_14 = fields.Monetary(
        string="[02-14] Base from export",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_15 = fields.Monetary(
        string="[02-15] Base for ICD",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_16 = fields.Monetary(
        string="[02-16] Base for Art.140, 146, 173 (21)",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_17 = fields.Monetary(
        string="[02-17] Base for Art.21",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_18 = fields.Monetary(
        string="[02-18] Base Art.62(2) on the territory of EU",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_19 = fields.Monetary(
        string="[02-19] Base sales exempt ICD",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_21 = fields.Monetary(
        string="[02-21] VAT taxation 20%",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_22 = fields.Monetary(
        string="[02-22] VAT ICA Art.82, ал.2-3",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_23 = fields.Monetary(
        string="[02-23] VAT Private usage",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_24 = fields.Monetary(
        string="[02-24] VAT travel services 9%",
        currency_field="company_currency_id",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL(
                f"""CREATE or REPLACE VIEW
{self._table} as ({self._table_query})"""
            )
        )

    @property
    def _table_query(self):
        where_clause = self._where()
        return f"""SELECT {self._select()}
FROM {self._from(where_clause=where_clause)}
{'WHERE ' + where_clause if where_clause else ''}
{'GROUP BY ' + self._group() or ''}"""

    @api.model
    def _select(self):
        return f"""am.company_id AS company_id,
        0 AS move_id,
        to_char(am.date, 'YYYYMM') AS info_tag_3,
        COUNT(accs.move_id) AS info_tag_5,
        COUNT(accs.move_id) AS info_tag_6,
        SUM(accs.account_tag_11) AS account_tag_11,
        SUM(accs.account_tag_21) AS account_tag_21,
        SUM(accs.account_tag_121 + accs.account_tag_122) AS account_tag_12,
        SUM(accs.account_tag_26) AS account_tag_26,
        {l10n_bg_odoo_compatible(self.env, 'tag_22')},
        SUM(accs.account_tag_23) AS account_tag_23,
        SUM(accs.account_tag_13) AS account_tag_13,
        SUM(accs.account_tag_24) AS account_tag_24,
        SUM(accs.account_tag_14) AS account_tag_14,
        SUM(accs.account_tag_15) AS account_tag_15,
        SUM(accs.account_tag_16) AS account_tag_16,
        SUM(accs.account_tag_17) AS account_tag_17,
        SUM(accs.account_tag_18) AS account_tag_18,
        SUM(accs.account_tag_19) AS account_tag_19,
        SUM(accs.account_tag_25) AS account_tag_25"""

    @api.model
    def _from(self, where_clause=""):
        return f"""account_move AS am
LEFT JOIN (SELECT move_id, date, account_tag_21, account_tag_11, account_tag_12, account_tag_121, account_tag_122,
                  account_tag_26, account_tag_23, account_tag_13, account_tag_24, account_tag_14, account_tag_15,
                  account_tag_16, account_tag_17, account_tag_18, account_tag_19, account_tag_25, account_tag_22
                  FROM account_bg_calc_sales_line{' WHERE ' + where_clause if where_clause else ''}) AS accs
    ON am.id = accs.move_id"""

    @api.model
    def _group(self):
        return """am.company_id, info_tag_3"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return ""
