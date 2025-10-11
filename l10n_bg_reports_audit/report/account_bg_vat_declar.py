# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    l10n_bg_extend_address,
    l10n_bg_lang,
    l10n_bg_odoo_compatible,
    l10n_bg_where,
    list_months_between_dates,
    account_tag_33_43
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
    # represent_contact_type = fields.Char(string="Represent contact type", readonly=True)

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
        return f"""acc.company_id AS company_id,
        COALESCE(company_partner.vat, company_partner.l10n_bg_uic) AS company_vat,
        CONCAT({l10n_bg_lang(self.env, lang_modules='partner', field_name='company_partner.city')}, ', ', {l10n_bg_lang(self.env, lang_modules='partner', field_name='company_partner.street')}) AS company_address,
        COALESCE(company_partner.vat, company_partner.l10n_bg_uic) AS info_tag_1,
        {l10n_bg_lang(self.env, lang_modules='partner', field_name='company_partner.name')} AS info_tag_2,
        info_tag_3,
        CONCAT(represent_partner.l10n_bg_uic, '/', {l10n_bg_lang(self.env, lang_modules='partner', field_name='represent_partner.name')}) AS info_tag_4,
        acc.info_tag_5,
        acc.info_tag_6,
        COALESCE(acc.account_tag_10, 0.0) AS account_tag_10,
        COALESCE(acc.account_tag_11, 0.0) AS account_tag_11,
        COALESCE(acc.account_tag_20, 0.0) AS account_tag_20,
        COALESCE(acc.account_tag_21, 0.0) AS account_tag_21,
        COALESCE(acc.account_tag_121, 0.0) + COALESCE(acc.account_tag_122, 0.0) AS account_tag_12,
        COALESCE(acc.account_tag_121, 0.0) AS account_tag_121,
        COALESCE(acc.account_tag_122, 0.0) AS account_tag_122,
        COALESCE(acc.account_tag_26, 0.0) AS account_tag_26,
        COALESCE(acc.account_tag_22, 0.0) AS account_tag_22,
        COALESCE(acc.account_tag_23, 0.0) AS account_tag_23,
        COALESCE(acc.account_tag_13, 0.0) AS account_tag_13,
        COALESCE(acc.account_tag_24, 0.0) AS account_tag_24,
        COALESCE(acc.account_tag_14, 0.0) AS account_tag_14,
        COALESCE(acc.account_tag_15, 0.0) AS account_tag_15,
        COALESCE(acc.account_tag_16, 0.0) AS account_tag_16,
        COALESCE(acc.account_tag_17, 0.0) AS account_tag_17,
        COALESCE(acc.account_tag_18, 0.0) AS account_tag_18,
        COALESCE(acc.account_tag_19, 0.0) AS account_tag_19,
        COALESCE(acc.account_tag_25, 0.0) AS account_tag_25,
        COALESCE(acc.account_tag_30, 0.0) AS account_tag_30,
        COALESCE(acc.account_tag_31, 0.0) AS account_tag_31,
        COALESCE(acc.account_tag_41 + account_tag_42*account_tag_33 + account_tag_43, 0.0) AS account_tag_40,
        COALESCE(acc.account_tag_41, 0.0) AS account_tag_41,
        COALESCE(acc.account_tag_32, 0.0) AS account_tag_32,
        COALESCE(acc.account_tag_33, 0.0) AS account_tag_33,
        COALESCE(acc.account_tag_42, 0.0) AS account_tag_42,
        COALESCE(acc.account_tag_43, 0.0) AS account_tag_43,
        COALESCE(acc.account_tag_44, 0.0) AS account_tag_44,
        COALESCE(acc.account_tag_50, 0.0) AS account_tag_50,
        COALESCE(acc.account_tag_60, 0.0) AS account_tag_60,
        COALESCE(acc.account_tag_70, 0.0) AS account_tag_70,
        COALESCE(acc.account_tag_71, 0.0) AS account_tag_71,
        COALESCE(acc.account_tag_80, 0.0) AS account_tag_80,
        COALESCE(acc.account_tag_81, 0.0) AS account_tag_81,
        COALESCE(acc.account_tag_82, 0.0) AS account_tag_82"""

    @api.model
    def _from(self):
        calc_declaration = self.env['account.bg.vat.calc.declar']._table_query
        return f"""({calc_declaration}) AS acc
LEFT JOIN res_company AS company
    ON acc.company_id = company.id
LEFT JOIN res_partner AS company_partner
    ON company.partner_id = company_partner.id
LEFT JOIN res_partner AS represent_partner
    ON company.l10n_bg_tax_contact_id = represent_partner.id""" + l10n_bg_extend_address(self.env)

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, tax_periods, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            if len(tax_periods) == 0:
                return f"""acc.company_id = {self.env.company.id} AND acc.state = ANY(ARRAY{state}) AND acc.info_tag_3 = '{tax_period}'"""
            else:
                return f"""acc.company_id = {self.env.company.id} AND acc.state = ANY(ARRAY{state}) AND acc.info_tag_3 = ANY(ARRAY{tax_periods})"""
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
        account_tag_33, account_tag_43 = 0.0, 0.0
        if self._context.get("report_options"):
            account_tag_33, account_tag_43 = account_tag_33_43(self.env, self._context.get("report_options"))
            if not account_tag_33:
                account_tag_33 = 0.0
            if not account_tag_43:
                account_tag_43 = 0.0

        return f""" am.company_id AS company_id,
        am.state AS state,
        to_char(am.date, 'YYYYMM') AS info_tag_3,
        COUNT(accs.move_id) AS info_tag_5,
        COUNT(accp.move_id) AS info_tag_6,
        SUM(accs.account_tag_11 + accs.account_tag_121 + accs.account_tag_122 + accs.account_tag_13 + accs.account_tag_15 + accs.account_tag_16 + accs.account_tag_17 + accs.account_tag_18 + accs.account_tag_19) AS account_tag_10,
        SUM(accs.account_tag_11) AS account_tag_11,
        SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24) AS account_tag_20,
        SUM(accs.account_tag_21) AS account_tag_21,
        SUM(accs.account_tag_121+accs.account_tag_122) AS account_tag_12,
        SUM(accs.account_tag_121) AS account_tag_121,
        SUM(accs.account_tag_122) AS account_tag_122,
        SUM(accs.account_tag_26) AS account_tag_26,
        SUM(accs.account_tag_22) AS account_tag_22,
        SUM(accs.account_tag_23) AS account_tag_23,
        SUM(accs.account_tag_13) AS account_tag_13,
        SUM(accs.account_tag_24) AS account_tag_24,
        SUM(accs.account_tag_14) AS account_tag_14,
        SUM(accs.account_tag_15) AS account_tag_15,
        SUM(accs.account_tag_16) AS account_tag_16,
        SUM(accs.account_tag_17) AS account_tag_17,
        SUM(accs.account_tag_18 + accs.account_tag_25) AS account_tag_18,
        SUM(accs.account_tag_19) AS account_tag_19,
        SUM(accs.account_tag_25) AS account_tag_25,
        SUM(accp.account_tag_30 + accp.account_tag_44) AS account_tag_30,
        SUM(accp.account_tag_31) AS account_tag_31,
        SUM(accp.account_tag_41 + accp.account_tag_42*{account_tag_33} + accp.account_tag_43) AS account_tag_40,
        SUM(accp.account_tag_41) AS account_tag_41,
        SUM(accp.account_tag_32) AS account_tag_32,
        SUM(accp.account_tag_42) AS account_tag_42,
        SUM(accp.account_tag_44) AS account_tag_44,
        {l10n_bg_odoo_compatible(self.env, 'tag_50', report_options=self._context.get("report_options") or {})} AS account_tag_50,
        {l10n_bg_odoo_compatible(self.env, 'tag_60', report_options=self._context.get("report_options") or {})} AS account_tag_60,
        SUM(accr.account_tag_70) AS account_tag_70,
        SUM(accr.account_tag_71) AS account_tag_71,
        SUM(accr.account_tag_80) AS account_tag_80,
        SUM(accr.account_tag_81) AS account_tag_81,
        SUM(accr.account_tag_82) AS account_tag_82,
        {account_tag_33} AS account_tag_33,
        {account_tag_43} AS account_tag_43"""

    @api.model
    def _from(self, where_clause=""):
        return f"""account_move AS am
LEFT JOIN (SELECT move_id, date, account_tag_21, account_tag_11, account_tag_12, account_tag_121, account_tag_122,
                  account_tag_26, account_tag_23, account_tag_13, account_tag_24, account_tag_14, account_tag_15,
                  account_tag_16, account_tag_17, account_tag_18, account_tag_19, account_tag_25, account_tag_22
            FROM ({self.env['account.bg.calc.sales.line']._table_query}) AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''})AS accs
    ON am.id = accs.move_id
LEFT JOIN (SELECT move_id, date, account_tag_30, account_tag_31, account_tag_41, account_tag_32, account_tag_42,
                  account_tag_43, account_tag_44 FROM ({self.env['account.bg.calc.purchases.line']._table_query}) AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''}) AS accp
    ON am.id = accp.move_id
LEFT JOIN (SELECT move_id, date, account_tag_50, account_tag_60, account_tag_70, account_tag_71, account_tag_80,
                  account_tag_81, account_tag_82
            FROM account_bg_vat_result_declar AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''}) AS accr
    ON am.id = accr.move_id"""

    @api.model
    def _group(self):
        return """am.company_id, state, info_tag_3"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, tax_periods, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return ""
