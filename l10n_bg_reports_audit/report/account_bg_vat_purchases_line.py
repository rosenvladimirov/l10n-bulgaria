# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

from odoo.addons.l10n_bg_reports_audit.models.account_move import (
    get_delivery_type,
    get_doc_type,
)
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    l10n_bg_lang,
    l10n_bg_where,
)

_logger = logging.getLogger(__name__)


class AccountBGInfoPurchasesLine(models.Model):
    """Model representing VAT lines for Analysis in Bulgarian Localization."""

    _name = "account.bg.info.purchases.line"
    _description = "VAT line information for Analysis in Bulgarian Localization"
    _auto = False
    _order = "move_id asc"

    company_id = fields.Many2one("res.company", "Company", readonly=True)
    move_id = fields.Many2one(
        "account.move", string="Account Move", readonly=True, auto_join=True
    )
    id = fields.Integer(string="ID", readonly=True, related="move_id.id")

    info_tag_1 = fields.Char(string="[02-01] Tax period", readonly=True)
    info_tag_2 = fields.Char(string="[02-02] TIN", readonly=True)
    info_tag_3 = fields.Char(string="[02-03] Office", readonly=True)
    info_tag_4 = fields.Integer(string="[02-04] Counter", readonly=True)
    info_tag_5 = fields.Selection(
        selection=get_doc_type(), string="[02-05] Vat type document", readonly=True
    )
    info_tag_6 = fields.Char(string="[02-06] Document number", readonly=True)
    info_tag_7 = fields.Date(string="[02-07] Document date", readonly=True)
    info_tag_8 = fields.Char(string="[02-08] Partner VAT", readonly=True)
    info_tag_9 = fields.Char(string="[02-09] Partner name", readonly=True)
    info_tag_10 = fields.Char(
        string="[02-10] Narration for audit report", readonly=True
    )
    info_tag_45 = fields.Selection(
        selection=get_delivery_type(), string="[02-45] Vat type delivery", readonly=True
    )

    @property
    def _table_query(self):
        where_clause = self._where()
        if self._context.get("report_options") and self._context["report_options"].get(
            "force_total", False
        ):
            report_options = self._context["report_options"].copy()
            report_options["force_total"] = False
            rows = self.with_context(
                dict(self._context, report_options=report_options)
            )._table_query
            total = self.env["account.bg.total.purchases.line"]._table_query
            return f"""{rows}
UNION
{total}"""

        return f"""SELECT {self._select()}
    FROM {self._from(where_clause=where_clause)}
    {where_clause and 'WHERE ' + where_clause or ''}"""

    @api.model
    def _select(self):
        lang = l10n_bg_lang(self.env, "partner")
        if self._context.get("report_options") and self._context["report_options"].get(
            "lang"
        ):
            lang = self._context["report_options"]["lang"]
        return f"""am.company_id AS company_id,
        am.id AS move_id,
        accp.info_tag_1 AS info_tag_1,
        COALESCE(company_partner.l10n_bg_uic, company_partner.vat) AS info_tag_2,
        company.l10n_bg_departament_code AS info_tag_3,
        ROW_NUMBER() OVER(ORDER BY am.date) AS info_tag_4,
        am.l10n_bg_doc_type AS info_tag_5,
        COALESCE(am.l10n_bg_name, LPAD(NULLIF(REGEXP_REPLACE(am.name, '\\D','','g'), '')::varchar(255), 10, '0')) AS info_tag_6,
        COALESCE(am.l10n_bg_date, am.invoice_date, am.date) AS info_tag_7,
        COALESCE(partner.vat, partner.l10n_bg_uic) AS info_tag_8,
        partner.name{lang} AS info_tag_9,
        am.l10n_bg_narration{lang} AS info_tag_10,
        am.l10n_bg_delivery_type AS info_tag_45,
        accp.account_tag_30,
        accp.account_tag_31,
        accp.account_tag_41,
        accp.account_tag_32,
        accp.account_tag_42,
        accp.account_tag_43,
        accp.account_tag_44"""

    @api.model
    def _from(self, where_clause=""):
        # LEFT JOIN (SELECT res_partner_id_number.id, res_partner_id_number.name, res_partner_id_number.partner_id FROM res_partner_id_number
        #         LEFT JOIN res_partner_id_category AS id_category
        #             ON res_partner_id_number.category_id = id_category.id
        #         WHERE id_category.name#>>'{en_US}' = 'bg_uic' LIMIT 1) AS id_number
        #     ON partner.id = id_number.partner_id
        return f"""account_move AS am
        JOIN (SELECT move_id, info_tag_1,
                     account_tag_30, account_tag_31, account_tag_41, account_tag_32, account_tag_42, account_tag_43, account_tag_44
                FROM account_bg_calc_purchases_line AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''}) AS accp
            ON am.id = accp.move_id
        LEFT JOIN res_partner AS partner
            ON am.partner_shipping_id = partner.id
        LEFT JOIN res_company AS company
            ON am.company_id = company.id
        LEFT JOIN res_partner AS company_partner
            ON company.partner_id = company_partner.id"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return False


class AccountBGCalcPurchasesLine(models.Model):
    """Base model for new Bulgarian VAT reports."""

    _name = "account.bg.calc.purchases.line"
    _description = "VAT line for Calculation Purchase in Bulgarian Localization"
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
    partner_id = fields.Many2one("res.partner", "Customer", readonly=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
    )
    info_tag_1 = fields.Char(string="[03-01] Tax period", readonly=True)
    account_tag_30 = fields.Monetary(
        string="[03-30] Base without tax credit",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_31 = fields.Monetary(
        string="[03-31] Base full tax credit",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_41 = fields.Monetary(
        string="[03-41] VAT full tax credit",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_32 = fields.Monetary(
        string="[03-32] Base partly tax credit",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_42 = fields.Monetary(
        string="[03-42] VAT partly tax credit",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_43 = fields.Monetary(
        string="[03-43] Annual adjustment - art. 73, paragraph 8",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_44 = fields.Monetary(
        string="[03-44] Base when acquiring goods from an intermediary in a tripartite operation",
        currency_field="company_currency_id",
        readonly=True,
    )

    def open_journal_entry(self):
        self.ensure_one()
        return self.move_id.get_formview_action()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        _logger.info(f"CREATE or REPLACE VIEW {self._table} as ({self._table_query})")
        self.env.cr.execute(
            sql.SQL(f"CREATE or REPLACE VIEW {self._table} as ({self._table_query})")
        )

    @property
    def _table_query(self):
        where_clauses = self._where()
        return f"""SELECT {self._select()}
    FROM {self._from()}
    {'WHERE ' + where_clauses if where_clauses else ''}
    {'GROUP BY ' + self._group() or ''}"""

    @api.model
    def _select(self):
        """Method to construct the 'WITH' clause of the SQL query."""
        return """am.company_id AS company_id,
    am.id AS id,
    am.id AS move_id,
    am.partner_id AS partner_id,
    am.state AS state,
    COALESCE(am.l10n_bg_date, am.date) AS date,
    to_char(am.date, 'YYYYMM') AS info_tag_1,
    SUM(CASE WHEN aat.tag_name = 30 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 30 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_30,
    SUM(CASE WHEN aat.tag_name = 31 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 31 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_31,
    SUM(CASE WHEN aat.tag_name = 41 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 41 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_41,
    SUM(CASE WHEN aat.tag_name = 32 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 32 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_32,
    SUM(CASE WHEN aat.tag_name = 42 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 42 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_42,
    SUM(CASE WHEN aat.tag_name = 43 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 43 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_43,
    SUM(CASE WHEN aat.tag_name = 44 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 44 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_44"""

    @api.model
    def _from(self):
        return """account_move_line AS aml
    LEFT JOIN account_move AS am
        ON aml.move_id = am.id
    LEFT JOIN account_account_tag_account_move_line_rel AS tag_line_rel
        ON tag_line_rel.account_move_line_id = aml.id
    LEFT JOIN (SELECT id,
                    NULLIF(REGEXP_REPLACE(account_account_tag.name#>>'{en_US}', '\\D','','g'), '')::numeric AS tag_name,
                    account_account_tag.tax_negate AS negate,
                    l10n_bg_applicability
                    FROM account_account_tag
                    WHERE applicability = 'taxes') AS aat
        ON aat.id = tag_line_rel.account_account_tag_id
    LEFT JOIN (SELECT imd.id, imd.res_id, imd.model, imd.module, imd.name
                    FROM ir_model_data AS imd
                    WHERE imd.module = 'l10n_bg' AND imd.model = 'account.account.tag') AS imd_tag_tax
        ON imd_tag_tax.res_id = aat.id"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND aat.l10n_bg_applicability = 'purchase' AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return """aat.l10n_bg_applicability = 'purchase'"""

    @api.model
    def _group(self):
        return """am.company_id, am.id, am.state, am.date, info_tag_1"""
