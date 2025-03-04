# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class AccountBGTotalViesDeclaration(models.Model):
    _name = "account.bg.vies.total.declar"
    _description = "VIES Declaration for Analysis in Bulgarian Localization"
    _auto = False
    _order = "company_id asc"

    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
    )

    info_tag_ttr_1 = fields.Char("[VDR-1] Main Record Section Code", readonly=True)
    account_tag_ttr_2 = fields.Monetary(
        readonly=True,
        string="[TTR-2] Base for ICD total [01-15]",
        currency_field="company_currency_id",
    )
    account_tag_ttr_3 = fields.Monetary(
        readonly=True,
        string="[TTR-3] Base for ICD",
        currency_field="company_currency_id",
    )
    info_tag_vhr_3 = fields.Integer(
        string="[VHR-3] Number of documents in the vies journal", readonly=True
    )
    info_tag_vir_7 = fields.Char(string="[02-01] Tax period", readonly=True)

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
        return """ am.company_id AS company_id,
            'TTR' AS info_tag_ttr_1,
            accv.info_tag_vir_7 AS info_tag_vir_7,
            am.state AS state,
            COUNT(accv.partner_id) AS info_tag_vhr_3,
            SUM(accv.account_tag_vir_4 + accv.account_tag_vir_5 + accv.account_tag_vir_6) AS account_tag_ttr_2,
            SUM(accv.account_tag_vir_4) AS account_tag_ttr_3"""

    @api.model
    def _from(self, where_clause=""):
        sub_select = self.env["account.bg.calc.vies.line"]._table_query
        return f"""account_move AS am
    LEFT JOIN (SELECT company_id, info_tag_vir_7, partner_id, account_tag_vir_4, account_tag_vir_5, account_tag_vir_6
                FROM ({sub_select}) AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''})AS accv
        ON am.company_id = accv.company_id"""

    @api.model
    def _group(self):
        return """am.company_id, accv.info_tag_vir_7, am.state"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            report_options = self._context.get("report_options")
            date_from = report_options["date"]["date_from"]
            date_from_date = fields.Date.from_string(date_from)
            tax_period = date_from_date.strftime("%Y%m")
            company_id = self.env.company.id
            unposted_in_period = report_options["unposted_in_period"]
            state = ["posted"]
            if unposted_in_period:
                state.append("draft")
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND info_tag_vir_7 = '{tax_period}'"""
        return ""
