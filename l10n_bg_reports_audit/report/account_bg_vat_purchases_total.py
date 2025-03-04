# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

from odoo.addons.l10n_bg_reports_audit.models.account_move import (
    get_delivery_type,
    get_doc_type,
)
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import l10n_bg_where

_logger = logging.getLogger(__name__)


class AccountBGTotalPurchasesLine(models.Model):
    """Base model for new Bulgarian VAT reports."""

    _name = "account.bg.total.purchases.line"
    _description = "VAT line Total for Purchase total in Bulgarian Localization"
    _rec_name = "info_tag_1"
    _auto = False
    _order = "company_id asc"

    move_id = fields.Integer(string="Total", readonly=True)
    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )

    info_tag_1 = fields.Char(string="[02-01] Tax period", readonly=True)
    info_tag_2 = fields.Char(string="[02-02] TIN", readonly=True)
    info_tag_3 = fields.Char(string="[02-03] Office", readonly=True)
    info_tag_4 = fields.Integer(string="[02-04] Counter", readonly=True)
    info_tag_5 = fields.Selection(
        selection=get_doc_type, string="[02-05] Vat type document", readonly=True
    )
    info_tag_6 = fields.Char(string="[02-06] Document number", readonly=True)
    info_tag_7 = fields.Date(string="[02-07] Document date", readonly=True)
    info_tag_8 = fields.Char(string="[02-08] Partner VAT", readonly=True)
    info_tag_9 = fields.Char(string="[02-09] Partner name", readonly=True)
    info_tag_10 = fields.Char(
        string="[02-10] Narration for audit report", readonly=True
    )
    info_tag_45 = fields.Selection(
        selection=get_delivery_type, string="[02-45] Vat type delivery", readonly=True
    )
    account_tag_30 = fields.Monetary(
        readonly=True,
        string="[02-30] Base for not entitled to a tax credit",
        currency_field="company_currency_id",
    )
    account_tag_31 = fields.Monetary(
        readonly=True,
        string="[02-31] Base for full tax credit",
        currency_field="company_currency_id",
    )
    account_tag_32 = fields.Monetary(
        readonly=True,
        string="[02-32] Base partly tax credit (~%)",
        currency_field="company_currency_id",
    )
    account_tag_41 = fields.Monetary(
        readonly=True,
        string="[02-41] VAT for full tax credit",
        currency_field="company_currency_id",
    )
    account_tag_42 = fields.Monetary(
        readonly=True,
        string="[02-42] VAT partly tax credit (~%)",
        currency_field="company_currency_id",
    )
    account_tag_43 = fields.Monetary(
        readonly=True,
        string="[02-43] Correction of Art.73, para. 8",
        currency_field="company_currency_id",
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
        return """ am.company_id AS company_id,
        0 AS move_id,
        COALESCE(company_partner.l10n_bg_uic, company_partner.vat) AS info_tag_2,
        accp.info_tag_1 AS info_tag_1,
        company.l10n_bg_departament_code AS info_tag_3,
        0 AS info_tag_4,
        NULL AS info_tag_5,
        NULL AS info_tag_6,
        NULL AS info_tag_7,
        NULL AS info_tag_8,
        NULL AS info_tag_9,
        NULL AS info_tag_10,
        NULL AS info_tag_45,
        SUM(accp.account_tag_30) AS account_tag_30,
        SUM(accp.account_tag_31) AS account_tag_31,
        SUM(accp.account_tag_41) AS account_tag_41,
        SUM(accp.account_tag_32) AS account_tag_32,
        SUM(accp.account_tag_42) AS account_tag_42,
        SUM(accp.account_tag_44) AS account_tag_44,
        SUM(accp.account_tag_43) AS account_tag_43"""

    @api.model
    def _from(self, where_clause=""):
        return f"""account_move AS am
LEFT JOIN (SELECT move_id, info_tag_1, account_tag_30, account_tag_31, account_tag_41, account_tag_32, account_tag_42,
account_tag_43, account_tag_44 FROM account_bg_calc_purchases_line{' WHERE ' + where_clause if where_clause else ''}) AS accp
        ON am.id = accp.move_id
LEFT JOIN res_company AS company
    ON am.company_id = company.id
LEFT JOIN res_partner AS company_partner
    ON company.partner_id = company_partner.id"""

    @api.model
    def _group(self):
        return """am.company_id, COALESCE(company_partner.l10n_bg_uic, company_partner.vat), accp.info_tag_1, company.l10n_bg_departament_code"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return ""
