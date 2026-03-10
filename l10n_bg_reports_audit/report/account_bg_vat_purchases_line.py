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
    l10n_bg_get_tag_negate_sql,
    l10n_bg_audit_tax_percentage,
)

_logger = logging.getLogger(__name__)


class AccountBGInfoPurchasesLine(models.Model):
    """Model representing VAT lines for Analysis in Bulgarian Localization."""

    _name = "account.bg.info.purchases.line"
    _description = "VAT line information for Analysis in Bulgarian Localization"
    _auto = False
    _order = "move_id asc"

    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True
    )
    move_id = fields.Many2one(
        "account.move", string="Account Move", readonly=True, auto_join=True
    )
    id = fields.Integer(string="ID", readonly=True, related="move_id.id")
    partner_id = fields.Many2one("res.partner", "Customer", readonly=True)

    info_tag_1 = fields.Char(
        string="[03-01] Tax period",
        help="Controls and rules: yes",
        readonly=True,
    )
    info_tag_2 = fields.Char(
        string="[03-02] VAT identification number of the person",
        help="Controls and rules: yes",
        readonly=True,
    )
    info_tag_3 = fields.Integer(
        string="[03-03] Branch/separate unit",
        readonly=True,
    )
    info_tag_4 = fields.Integer(
        string="[03-04] Sequential document number in the journal",
        readonly=True,
    )
    info_tag_5 = fields.Selection(
        selection=get_doc_type(),
        string="[03-05] Document type",
        readonly=True,
    )
    info_tag_6 = fields.Char(string="[03-06] Document number", readonly=True)
    info_tag_7 = fields.Date(string="[03-07] Document date", readonly=True)
    info_tag_8 = fields.Char(
        string="[03-08] Counterparty (supplier) VAT ID",
        readonly=True,
    )
    info_tag_9 = fields.Char(
        string="[03-09] Counterparty (supplier) name",
        readonly=True,
    )
    info_tag_10 = fields.Char(
        string="[03-10] Type of goods or scope and type of service - exact description according to the document",
        readonly=True,
    )
    info_tag_45 = fields.Selection(
        selection=get_delivery_type(),
        string="[03-45] Supply under Art. 163a or import under Art. 167a of the VAT Act",
        help="Controls and rules: no",
        readonly=True,
    )

    account_tag_30 = fields.Monetary(
        string="[03-30] Tax base and tax of received supplies, ICAs, received supplies under Art. 82(2)-(5) VAT Act and imports without tax credit or without tax",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_31 = fields.Monetary(
        string="[03-31] Tax base of received supplies, ICAs, received supplies under Art. 82(2)-(5) VAT Act, imports, and tax base of received supplies used for supplies under Art. 69(2) VAT Act with full tax credit",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_41 = fields.Monetary(
        string="[03-41] VAT with full tax credit",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_32 = fields.Monetary(
        string="[03-32] Tax base of received supplies, ICAs, received supplies under Art. 82(2)-(5) VAT Act, imports, and tax base of received supplies used for supplies under Art. 69(2) VAT Act with partial tax credit",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_42 = fields.Monetary(
        string="[03-42] VAT with partial tax credit",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_43 = fields.Monetary(
        string="[03-43] Annual adjustment under Art. 73(8) VAT Act",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_44 = fields.Monetary(
        string="[03-44] Tax base on acquisition of goods from an intermediary in a triangular transaction",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )

    @property
    def _table_query(self):
        where_clause = self._where()
        order_clause = self._order_clause()
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
    {where_clause and 'WHERE ' + where_clause or ''} ORDER BY {order_clause}"""

    @api.model
    def _select(self):
        return f"""am.company_id AS company_id,
        am.id AS move_id,
        am.partner_id AS partner_id,
        accp.info_tag_1 AS info_tag_1,
        COALESCE(company_partner.vat, company_partner.l10n_bg_uic) AS info_tag_2,
        company.l10n_bg_departament_code AS info_tag_3,
        ROW_NUMBER() OVER(ORDER BY am.date) AS info_tag_4,
        am.l10n_bg_document_type AS info_tag_5,
        COALESCE(am.l10n_bg_name, am.ref, LPAD(NULLIF(REGEXP_REPLACE(am.name, '\\D','','g'), '')::varchar(255), 10, '0')) AS info_tag_6,
        COALESCE(am.l10n_bg_date, am.invoice_date, am.date) AS info_tag_7,
        COALESCE(partner.vat, partner.l10n_bg_uic) AS info_tag_8,
        {l10n_bg_lang(self.env, "partner", "partner.name")} AS info_tag_9,
        {l10n_bg_lang(self.env, "narration")} AS info_tag_10,
        am.l10n_bg_exemption_reason AS info_tag_45,
        accp.account_tag_30 AS account_tag_30,
        accp.account_tag_31 AS account_tag_31,
        accp.account_tag_41 AS account_tag_41,
        accp.account_tag_32 AS account_tag_32,
        accp.account_tag_42 AS account_tag_42,
        accp.account_tag_43 AS account_tag_43,
        accp.account_tag_44 AS account_tag_44"""

    @api.model
    def _from(self, where_clause=""):
        return f"""account_move AS am
        JOIN (SELECT move_id, info_tag_1,
                     account_tag_30, account_tag_31, account_tag_41, account_tag_32, account_tag_42, account_tag_43, account_tag_44
                FROM ({self.env['account.bg.calc.purchases.line']._table_query}) AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''}) AS accp
            ON am.id = accp.move_id
        LEFT JOIN res_partner AS partner
            ON am.partner_id = partner.id
        LEFT JOIN res_company AS company
            ON am.company_id = company.id
        LEFT JOIN res_partner AS company_partner
            ON company.partner_id = company_partner.id"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, tax_periods, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options"),
                model_report='purchase',
            )
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return False

    @api.model
    def _order_clause(self):
        return """am.date ASC"""


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
    info_tag_1 = fields.Char(
        string="[03-01] Tax period",
        help="Controls and rules: yes",
        readonly=True,
    )
    account_tag_30 = fields.Monetary(
        string="[03-30] Tax base and tax of received supplies, ICAs, received supplies under Art. 82(2)-(5) VAT Act and imports without tax credit or without tax",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_31 = fields.Monetary(
        string="[03-31] Tax base of received supplies, ICAs, received supplies under Art. 82(2)-(5) VAT Act, imports, and tax base of received supplies used for supplies under Art. 69(2) VAT Act with full tax credit",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_41 = fields.Monetary(
        string="[03-41] VAT with full tax credit",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_32 = fields.Monetary(
        string="[03-32] Tax base of received supplies, ICAs, received supplies under Art. 82(2)-(5) VAT Act, imports, and tax base of received supplies used for supplies under Art. 69(2) VAT Act with partial tax credit",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_42 = fields.Monetary(
        string="[03-42] VAT with partial tax credit",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_43 = fields.Monetary(
        string="[03-43] Annual adjustment under Art. 73(8) VAT Act",
        help="Controls and rules: yes",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_44 = fields.Monetary(
        string="[03-44] Tax base on acquisition of goods from an intermediary in a triangular transaction",
        help="Controls and rules: yes",
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
        account_tag_31_expr = l10n_bg_audit_tax_percentage(self.env, "aml.balance")
        return f"""am.company_id AS company_id,
    am.id AS id,
    am.id AS move_id,
    am.partner_id AS partner_id,
    am.state AS state,
    am.date AS date,
    to_char(am.date, 'YYYYMM') AS info_tag_1,
    SUM(CASE
        WHEN am.state = 'cancel' THEN 0.00
        WHEN aat.tag_name = 30 AND aat.negate THEN aml.balance
        WHEN aat.tag_name = 30 AND NOT aat.negate THEN aml.balance
        ELSE 0.00
        END) AS account_tag_30,
    {account_tag_31_expr} AS account_tag_31,
    SUM(CASE
        WHEN am.state = 'cancel' THEN 0.00
        WHEN aat.tag_name = 41 AND aat.negate THEN aml.balance
        WHEN aat.tag_name = 41 AND NOT aat.negate THEN aml.balance
        ELSE 0.00
        END) AS account_tag_41,
    SUM(CASE
        WHEN am.state = 'cancel' THEN 0.00
        WHEN aat.tag_name = 32 AND aat.negate THEN aml.balance
        WHEN aat.tag_name = 32 AND NOT aat.negate THEN aml.balance
        ELSE 0.00
        END) AS account_tag_32,
    SUM(CASE
        WHEN am.state = 'cancel' THEN 0.00
        WHEN aat.tag_name = 42 AND aat.negate THEN aml.balance
        WHEN aat.tag_name = 42 AND NOT aat.negate THEN aml.balance
        ELSE 0.00
        END) AS account_tag_42,
    SUM(CASE
        WHEN am.state = 'cancel' THEN 0.00
        WHEN aat.tag_name = 43 AND aat.negate THEN aml.balance
        WHEN aat.tag_name = 43 AND NOT aat.negate THEN aml.balance
        ELSE 0.00
        END) AS account_tag_43,
    SUM(CASE
        WHEN am.state = 'cancel' THEN 0.00
        WHEN aat.tag_name = 44 AND aat.negate THEN aml.balance
        WHEN aat.tag_name = 44 AND NOT aat.negate THEN aml.balance
        ELSE 0.00
        END) AS account_tag_44"""

    @api.model
    def _from(self):
        tax_negate = l10n_bg_get_tag_negate_sql(table_alias='account_account_tag')
        return f"""account_move_line AS aml
    LEFT JOIN account_move AS am
        ON aml.move_id = am.id
    LEFT JOIN account_account_tag_account_move_line_rel AS tag_line_rel
        ON tag_line_rel.account_move_line_id = aml.id
    LEFT JOIN (SELECT id,
                    NULLIF(REGEXP_REPLACE(account_account_tag.name#>>'{{en_US}}', '\\D','','g'), '')::numeric AS tag_name,
                    {tax_negate},
                    l10n_bg_applicability
                    FROM account_account_tag
                    WHERE applicability = 'taxes') AS aat
        ON aat.id = tag_line_rel.account_account_tag_id
"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            date_from, date_to, tax_period, tax_periods, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND aat.l10n_bg_applicability = 'purchase' AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return """aat.l10n_bg_applicability = 'purchase'"""

    @api.model
    def _group(self):
        return """am.company_id, am.id, am.state, am.date, info_tag_1"""
