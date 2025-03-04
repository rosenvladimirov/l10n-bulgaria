# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    l10n_bg_lang,
    l10n_bg_odoo_compatible,
    l10n_bg_where,
)

_logger = logging.getLogger(__name__)


class AccountBgVatInfoDeclar(models.Model):
    _name = "account.bg.vat.info.declar"
    _description = "VAT declaration for Analysis in Bulgarian Localization"
    _auto = False
    _order = "company_id desc"

    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_vat = fields.Char(string="UIC", readonly=True)
    company_address = fields.Char(string="Company address", readonly=True)

    info_tag_1 = fields.Char(string="TIN", readonly=True)
    info_tag_2 = fields.Char(string="[00-02] Name of the Legal Entity", readonly=True)
    info_tag_3 = fields.Char(string="[00-03] Tax period", readonly=True)
    info_tag_4 = fields.Char(
        string="[00-04] Person submitting the data (TIN/name)", readonly=True
    )
    info_tag_5 = fields.Integer(
        string="[00-05] Number of documents in the sales journal", readonly=True
    )
    info_tag_6 = fields.Integer(
        string="[00-06] Number of documents in the purchase journal", readonly=True
    )

    @property
    def _table_query(self):
        return f"""SELECT {self._select()}
    FROM {self._from()}
        {self._where() and 'WHERE ' + self._where() or ''}
        {self._group() and 'GROUP BY ' + self._group() or ''}"""

    @api.model
    def _select(self):
        lang = l10n_bg_lang(self.env)
        lang_ext = l10n_bg_lang(self.env, "partner")
        if self._context.get("report_options") and self._context["report_options"].get(
            "lang"
        ):
            lang = self._context["report_options"]["lang"]
        return f"""acc.company_id AS company_id,
        COALESCE(company_partner.vat, company_partner.l10n_bg_uic) AS company_vat,
        CONCAT (company_partner.city{lang}, ', ', company_partner.street{lang}) AS company_address,
        company_partner.l10n_bg_uic AS info_tag_1,
        company_partner.name{lang_ext} AS info_tag_2,
        info_tag_3,
        CONCAT (represent_partner.l10n_bg_uic, ' ', represent_partner.name{lang_ext}) AS info_tag_4,
        acc.info_tag_5,
        acc.info_tag_6,
        acc.account_tag_10,
        acc.account_tag_11,
        acc.account_tag_20,
        acc.account_tag_21,
        acc.account_tag_121 + acc.account_tag_122 AS account_tag_12,
        acc.account_tag_121,
        acc.account_tag_122,
        acc.account_tag_26,
        acc.account_tag_22,
        acc.account_tag_23,
        acc.account_tag_13,
        acc.account_tag_24,
        acc.account_tag_14,
        acc.account_tag_15,
        acc.account_tag_16,
        acc.account_tag_17,
        acc.account_tag_18,
        acc.account_tag_19,
        acc.account_tag_25,
        acc.account_tag_30,
        acc.account_tag_31,
        acc.account_tag_40,
        acc.account_tag_41,
        acc.account_tag_32,
        acc.account_tag_33,
        acc.account_tag_42,
        acc.account_tag_43,
        acc.account_tag_44,
        acc.account_tag_50,
        acc.account_tag_60,
        acc.account_tag_70,
        acc.account_tag_71,
        acc.account_tag_80,
        acc.account_tag_81,
        acc.account_tag_82"""

    @api.model
    def _from(self):
        return """account_bg_vat_calc_declar AS acc
LEFT JOIN res_company AS company
    ON acc.company_id = company.id
LEFT JOIN res_partner AS company_partner
    ON company.partner_id = company_partner.id
LEFT JOIN res_partner AS represent_partner
    ON company.l10n_bg_tax_contact_id = represent_partner.id"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            report_options = self._context.get("report_options")
            date_from = report_options["date"]["date_from"]
            date_from_date = fields.Date.from_string(date_from)
            tax_period = date_from_date.strftime("%Y%m")
            return f"""acc.company_id = {self.env.company.id} AND acc.info_tag_3 = '{tax_period}'"""
        return f"""acc.company_id = {self.env.company.id}"""

    @api.model
    def _group(self):
        return """"""


class AccountBGCalcDeclar(models.Model):
    """Base model for new Bulgarian VAT reports."""

    _name = "account.bg.vat.calc.declar"
    _description = "VAT line for Analysis in Bulgarian Localization"
    _auto = False
    _order = "company_id asc"

    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )
    info_tag_3 = fields.Char(string="[00-03] Tax period", readonly=True)
    info_tag_5 = fields.Integer(string="Counter sales", readonly=True)
    info_tag_6 = fields.Integer(string="Counter purchases", readonly=True)
    account_tag_10 = fields.Monetary(
        readonly=True,
        string="[01-10] Total amount of base",
        currency_field="company_currency_id",
        help="Total amount of base",
    )
    account_tag_20 = fields.Monetary(
        readonly=True, string="[01-20] Total VAT", currency_field="company_currency_id"
    )
    account_tag_11 = fields.Monetary(
        readonly=True,
        string="[01-11] Base for domestic taxation (20%)",
        currency_field="company_currency_id",
        help="Base amount from sales for domestic taxation (20%)",
    )
    account_tag_12 = fields.Monetary(
        readonly=True,
        string="[01-12] Base for ICA",
        currency_field="company_currency_id",
        help="Base amount for ICD and tax basis "
        "of received supplies under Art. 82, para. 2 - 5 VAT",
    )
    account_tag_121 = fields.Monetary(
        readonly=True,
        string="[01-12-1] Base for ICA",
        currency_field="company_currency_id",
        help="Base amount for ICD and tax basis "
        "of received supplies under Art. 82, para. 2 - 5 VAT",
    )
    account_tag_122 = fields.Monetary(
        readonly=True,
        string="[01-12-2] Base for ICA",
        currency_field="company_currency_id",
        help="Base amount for ICD and tax basis "
        "of received supplies under Art. 82, para. 2 - 5 VAT",
    )
    account_tag_13 = fields.Monetary(
        readonly=True,
        string="[01-13] Base travel services 9%",
        currency_field="company_currency_id",
    )
    account_tag_14 = fields.Monetary(
        readonly=True,
        string="[01-14] Base from export",
        currency_field="company_currency_id",
    )
    account_tag_15 = fields.Monetary(
        readonly=True,
        string="[01-15] Base for ICD",
        currency_field="company_currency_id",
    )
    account_tag_16 = fields.Monetary(
        readonly=True,
        string="[01-16] Base for Art.140, 146, 173 (21)",
        currency_field="company_currency_id",
    )
    account_tag_17 = fields.Monetary(
        readonly=True,
        string="[01-17] Base for Art.21",
        currency_field="company_currency_id",
    )
    account_tag_18 = fields.Monetary(
        readonly=True,
        string="[01-18] Base Art.62(2) on the territory of EU",
        currency_field="company_currency_id",
    )
    account_tag_19 = fields.Monetary(
        readonly=True,
        string="[01-19] Base sales exempt ICD",
        currency_field="company_currency_id",
    )
    account_tag_21 = fields.Monetary(
        readonly=True,
        string="[01-21] VAT taxation 20%",
        currency_field="company_currency_id",
    )
    account_tag_22 = fields.Monetary(
        readonly=True,
        string="[01-22] VAT ICA Art.82, ал.2-3",
        currency_field="company_currency_id",
    )
    account_tag_23 = fields.Monetary(
        readonly=True,
        string="[01-23] VAT Private usage",
        currency_field="company_currency_id",
    )
    account_tag_24 = fields.Monetary(
        readonly=True,
        string="[01-24] VAT travel services 9%",
        currency_field="company_currency_id",
    )
    account_tag_30 = fields.Monetary(
        readonly=True,
        string="[01-30] Base for not entitled to a tax credit",
        currency_field="company_currency_id",
    )
    account_tag_31 = fields.Monetary(
        readonly=True,
        string="[01-31] Base for full tax credit",
        currency_field="company_currency_id",
    )
    account_tag_32 = fields.Monetary(
        readonly=True,
        string="[01-32] Base partly tax credit (~%)",
        currency_field="company_currency_id",
    )
    account_tag_33 = fields.Monetary(
        readonly=True,
        string="[01-33] Coefficient Art.73,ал.5",
        currency_field="company_currency_id",
    )
    account_tag_40 = fields.Monetary(
        readonly=True,
        string="[01-40] VAT Total of tax credit",
        currency_field="company_currency_id",
    )
    account_tag_41 = fields.Monetary(
        readonly=True,
        string="[01-41] VAT for full tax credit",
        currency_field="company_currency_id",
    )
    account_tag_42 = fields.Monetary(
        readonly=True,
        string="[01-42] VAT partly tax credit (~%)",
        currency_field="company_currency_id",
    )
    account_tag_43 = fields.Monetary(
        readonly=True,
        string="[01-43] Correction of Art.73, para. 8",
        currency_field="company_currency_id",
    )
    account_tag_44 = fields.Monetary(
        readonly=True,
        string="[01-44] Base when acquiring goods from an intermediary in a tripartite operation",
        currency_field="company_currency_id",
    )
    account_tag_50 = fields.Monetary(
        readonly=True, string="[01-50] VAT to pay", currency_field="company_currency_id"
    )
    account_tag_60 = fields.Monetary(
        readonly=True,
        string="[01-60] VAT recovery",
        currency_field="company_currency_id",
    )
    account_tag_70 = fields.Monetary(
        readonly=True,
        string="[01-70] VAT deducted art.92, para. 1",
        currency_field="company_currency_id",
    )
    account_tag_71 = fields.Monetary(
        readonly=True,
        string="[01-71] VAT payed effectively",
        currency_field="company_currency_id",
    )
    account_tag_80 = fields.Monetary(
        readonly=True,
        string="[01-80] VAT reimbursement Art.92, para. 1",
        currency_field="company_currency_id",
    )
    account_tag_81 = fields.Monetary(
        readonly=True,
        string="[01-81] VAT reimbursement Art.92, para. 2",
        currency_field="company_currency_id",
    )
    account_tag_82 = fields.Monetary(
        readonly=True,
        string="[01-82] VAT reimbursement Art.92, para. 3",
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
        return f""" am.company_id AS company_id,
        to_char(am.date, 'YYYYMM') AS info_tag_3,
        COUNT(accs.move_id) AS info_tag_5,
        COUNT(accp.move_id) AS info_tag_6,
        SUM(accs.account_tag_11 + accs.account_tag_121 + accs.account_tag_122 + accs.account_tag_13 + accs.account_tag_15 + accs.account_tag_16 + accs.account_tag_17 + accs.account_tag_18 + accs.account_tag_19) AS account_tag_10,
        SUM(accs.account_tag_11) AS account_tag_11,
        {l10n_bg_odoo_compatible(self.env, 'tag_20')},
        SUM(accs.account_tag_21) AS account_tag_21,
        SUM(accs.account_tag_121+accs.account_tag_122) AS account_tag_12,
        SUM(accs.account_tag_121) AS account_tag_121,
        SUM(accs.account_tag_122) AS account_tag_122,
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
        SUM(accs.account_tag_25) AS account_tag_25,
        SUM(accp.account_tag_30) AS account_tag_30,
        SUM(accp.account_tag_31) AS account_tag_31,
        SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43) AS account_tag_40,
        SUM(accp.account_tag_41) AS account_tag_41,
        SUM(accp.account_tag_32) AS account_tag_32,
        SUM(accp.account_tag_42) AS account_tag_42,
        SUM(accp.account_tag_44) AS account_tag_44,
        {l10n_bg_odoo_compatible(self.env, 'tag_50')},
        {l10n_bg_odoo_compatible(self.env, 'tag_60')},
        SUM(accr.account_tag_70) AS account_tag_70,
        SUM(accr.account_tag_71) AS account_tag_71,
        SUM(accr.account_tag_80) AS account_tag_80,
        SUM(accr.account_tag_81) AS account_tag_81,
        SUM(accr.account_tag_82) AS account_tag_82,
        0.0 AS account_tag_33, 0.0 AS account_tag_43"""

    @api.model
    def _from(self, where_clause=""):
        return f"""account_move AS am
LEFT JOIN (SELECT move_id, date, account_tag_21, account_tag_11, account_tag_12, account_tag_121, account_tag_122,
                  account_tag_26, account_tag_23, account_tag_13, account_tag_24, account_tag_14, account_tag_15,
                  account_tag_16, account_tag_17, account_tag_18, account_tag_19, account_tag_25, account_tag_22
            FROM account_bg_calc_sales_line AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''})AS accs
    ON am.id = accs.move_id
LEFT JOIN (SELECT move_id, date, account_tag_30, account_tag_31, account_tag_41, account_tag_32, account_tag_42,
                  account_tag_43, account_tag_44 FROM account_bg_calc_purchases_line AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''}) AS accp
    ON am.id = accp.move_id
LEFT JOIN (SELECT move_id, date, account_tag_50, account_tag_60, account_tag_70, account_tag_71, account_tag_80,
                  account_tag_81, account_tag_82
            FROM account_bg_vat_result_declar AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''}) AS accr
    ON am.id = accr.move_id"""

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
