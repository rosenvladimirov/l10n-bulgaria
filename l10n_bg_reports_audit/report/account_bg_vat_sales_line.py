# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

from odoo.addons.l10n_bg_reports_audit.models.account_move import get_doc_type
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    l10n_bg_lang,
    l10n_bg_where,
)

_logger = logging.getLogger(__name__)


class AccountBGInfoSaleLine(models.Model):
    """Base model for new Bulgarian VAT reports. The idea is that these lines have all the necessary data and which any
    changes in odoo, these will be taken for this cube and then no changes will be needed in the reports that use
     these lines. A line is created for each accountring entry affected by VAT tax.

    Basically which it does is covert the accounting entries into columns depending on the information of the taxes and
    add some other fields"""

    _name = "account.bg.info.sale.line"
    _description = "VAT line information for Analysis in Bulgarian Localization"
    _auto = False
    _order = "date asc, move_id asc"

    date = fields.Date(string="Document date", readonly=True)
    company_id = fields.Many2one("res.company", "Company", readonly=True)
    move_id = fields.Many2one(
        "account.move", string="Account Move", readonly=True, auto_join=True
    )
    id = fields.Integer(string="ID", readonly=True, related="move_id.id")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
    )
    info_tag_0 = fields.Char(string="TIN", readonly=True)
    info_tag_1 = fields.Char(string="[02-01] Tax period", readonly=True)
    info_tag_2 = fields.Char(string="Office", readonly=True)
    info_tag_3 = fields.Integer(string="Counter", readonly=True)
    info_tag_4 = fields.Selection(
        selection=get_doc_type, string="Vat type document", readonly=True
    )
    info_tag_5 = fields.Char(string="Document number", readonly=True)
    info_tag_6 = fields.Date(string="Document date", readonly=True)
    info_tag_7 = fields.Char(string="Partner TIN", readonly=True)
    info_tag_8 = fields.Char(string="Partner name", readonly=True)
    info_tag_9 = fields.Char(string="Narration for audit report", readonly=True)
    info_tag_27 = fields.Char(
        string="Delivery according to Art. 163a or import under Art. 167a of the VAT",
        readonly=True,
    )

    @property
    def _table_query(self):
        where_clause = self._where()
        return f"""SELECT {self._select()}
    FROM {self._from(where_clause=where_clause)} {where_clause and 'WHERE ' + where_clause or ''}"""

    @api.model
    def _select(self):
        lang = l10n_bg_lang(self.env, "partner")
        if self._context.get("report_options") and self._context["report_options"].get(
            "lang"
        ):
            lang = self._context["report_options"]["lang"]
        return f""" am.company_id AS company_id,
        am.id AS move_id,
        am.state AS state,
        COALESCE(company_partner.vat, company_partner.l10n_bg_uic) AS info_tag_0,
        accs.info_tag_1 AS info_tag_1,
        company.l10n_bg_departament_code AS info_tag_2,
        ROW_NUMBER() OVER(ORDER BY am.date) AS info_tag_3,
        am.l10n_bg_doc_type AS info_tag_4,
        COALESCE(am.l10n_bg_name, LPAD(NULLIF(REGEXP_REPLACE(am.name, '\\D','','g'), '')::varchar(255), 10, '0')) AS info_tag_5,
        COALESCE(am.l10n_bg_date, am.invoice_date, am.date) AS info_tag_6,
        COALESCE(partner.vat, partner.l10n_bg_uic) AS info_tag_7,
        partner.name{lang} AS info_tag_8,
        am.l10n_bg_narration{lang} AS info_tag_9,
        am.l10n_bg_delivery_type AS info_tag_27,
        accs.account_tag_11 + accs.account_tag_121 + accs.account_tag_122 + accs.account_tag_13 + accs.account_tag_15 + accs.account_tag_16 + accs.account_tag_17 + accs.account_tag_18 + accs.account_tag_19 AS account_tag_10,
        accs.account_tag_11,
        accs.account_tag_121 + accs.account_tag_122 AS account_tag_12,
        accs.account_tag_121,
        accs.account_tag_122,
        accs.account_tag_13,
        accs.account_tag_14,
        accs.account_tag_15,
        accs.account_tag_16,
        accs.account_tag_17,
        accs.account_tag_18,
        accs.account_tag_19,
        accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24 AS account_tag_20,
        accs.account_tag_21,
        accs.account_tag_26,
        accs.account_tag_22,
        accs.account_tag_23,
        accs.account_tag_24,
        accs.account_tag_25"""

    @api.model
    def _from(self, where_clause=""):
        # LEFT JOIN (SELECT res_partner_id_number.id, res_partner_id_number.name, res_partner_id_number.partner_id FROM res_partner_id_number
        #         LEFT JOIN res_partner_id_category AS id_category
        #             ON res_partner_id_number.category_id = id_category.id
        #         WHERE id_category.name#>>'{en_US}' = 'bg_uic' LIMIT 1) AS id_number
        #     ON partner.id = id_number.partner_id
        return f""" account_move AS am
        JOIN (SELECT move_id, info_tag_1, account_tag_21, account_tag_12, account_tag_121, account_tag_122,
                     account_tag_26, account_tag_23, account_tag_13, account_tag_24, account_tag_14, account_tag_15,
                     account_tag_16, account_tag_17, account_tag_18,
                     account_tag_19, account_tag_25, account_tag_11, account_tag_22
                FROM account_bg_calc_sales_line AS acc{' WHERE ' + where_clause.replace('am.', 'acc.') if where_clause else ''}) AS accs
            ON am.id = accs.move_id
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
        return """"""


class AccountBGCalcSalesLine(models.Model):
    """Base model for new Bulgarian VAT reports. The idea is that these lines have all the necessary data and which any
    changes in odoo, these will be taken for this cube and then no changes will be needed in the reports that use
     these lines. A line is created for each accountring entry affected by VAT tax.

    Basically which it does is covert the accounting entries into columns depending on the information of the taxes and
    add some other fields"""

    _name = "account.bg.calc.sales.line"
    _description = "VAT line for Analysis in Bulgarian Localization"
    _auto = False
    _order = "move_id asc"

    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )

    move_id = fields.Many2one("account.move", string="Account Move", readonly=True)
    id = fields.Integer(string="ID", readonly=True, related="move_id.id")

    date = fields.Date(related="move_id.date", readonly=True)
    partner_id = fields.Many2one("res.partner", "Customer", readonly=True)

    info_tag_1 = fields.Char(string="[02-01] Tax period", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
    )
    account_tag_20 = fields.Monetary(
        string="[02-20] All VAT charged",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_11 = fields.Monetary(
        string="[02-11] Base for taxation with 20%",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_21 = fields.Monetary(
        string="[02-21] VAT 20%", currency_field="company_currency_id", readonly=True
    )
    account_tag_12 = fields.Monetary(
        string="[02-12] Base ICA", currency_field="company_currency_id", readonly=True
    )
    account_tag_121 = fields.Monetary(
        string="[02-12-1] Base ICA (1)",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_122 = fields.Monetary(
        string="[02-12-2] Base ICA (2)",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_26 = fields.Monetary(
        string="[02-26] Base art. 82, paragraphs 2-5",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_22 = fields.Monetary(
        string="[02-22] VAT ICA and art. 82, par. 2-5",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_23 = fields.Monetary(
        string="[02-23] VAT-personal needs",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_14 = fields.Monetary(
        string="[02-14] Base export 0%",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_15 = fields.Monetary(
        string="[02-15] Base ICD of goods 0%",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_16 = fields.Monetary(
        string="[02-16] Base 0% under Art. 140, par, 1 and Art. 173",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_17 = fields.Monetary(
        readonly=True,
        string="[02-17] Base under Art. 21 on the territory of the EU",
        currency_field="company_currency_id",
    )
    account_tag_18 = fields.Monetary(
        string="[02-18] Base under Art. 69, paragraph 2 on the territory of the EU",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_19 = fields.Monetary(
        string="[02-19] Base educated and ICA",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_24 = fields.Monetary(
        string="[02-24] VAT-tourist services 9%",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_25 = fields.Monetary(
        string="[02-25] TO-trilateral operations",
        currency_field="company_currency_id",
        readonly=True,
    )

    def open_journal_entry(self):
        self.ensure_one()
        return self.move_id.get_formview_action()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        #         _logger.info(f"""CREATE or REPLACE VIEW
        # {self._table} as ({self._table_query})""")
        self.env.cr.execute(
            sql.SQL(
                f"""CREATE or REPLACE VIEW
{self._table} as ({self._table_query})"""
            )
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
        return """am.company_id AS company_id,
    am.id AS id,
    am.id AS move_id,
    am.partner_id AS partner_id,
    am.state AS state,
    COALESCE(am.l10n_bg_date, am.date) AS date,
    to_char(am.date, 'YYYYMM') AS info_tag_1,
    SUM(CASE WHEN aat.tag_name = 11 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 11 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_11,
    SUM(CASE WHEN aat.tag_name = ANY(ARRAY[21,22,23]) AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = ANY(ARRAY[21,22,23]) AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_20,
    SUM(CASE WHEN aat.tag_name = 21 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 21 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_21,
    SUM(CASE WHEN aat.tag_name = 12 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 12 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_12,
    SUM(CASE WHEN aat.tag_name = 121 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 121 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_121,
    SUM(CASE WHEN aat.tag_name = 122 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 122 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_122,
    SUM(CASE WHEN aat.tag_name = 26 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 26 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_26,
    SUM(CASE WHEN aat.tag_name = 22 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 22 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_22,
    SUM(CASE WHEN aat.tag_name = 23 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 23 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_23,
    SUM(CASE WHEN aat.tag_name = 13 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 13 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_13,
    SUM(CASE WHEN aat.tag_name = 24 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 24 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_24,
    SUM(CASE WHEN aat.tag_name = 14 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 14 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_14,
    SUM(CASE WHEN aat.tag_name = 15 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 15 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_15,
    SUM(CASE WHEN aat.tag_name = 16 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 16 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_16,
    SUM(CASE WHEN aat.tag_name = 17 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 17 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_17,
    SUM(CASE WHEN aat.tag_name = 18 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 18 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_18,
    SUM(CASE WHEN aat.tag_name = 19 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 19 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_19,
    SUM(CASE WHEN aat.tag_name = 25 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 25 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_25"""

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
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND aat.l10n_bg_applicability = 'sale' AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return """aat.l10n_bg_applicability = 'sale'"""

    @api.model
    def _group(self):
        return """am.company_id, am.id, am.partner_id, am.state, am.date"""
