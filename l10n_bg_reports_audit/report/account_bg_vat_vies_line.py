# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import l10n_bg_where

_logger = logging.getLogger(__name__)


class AccountBGCalcViesLine(models.Model):
    _name = "account.bg.calc.vies.line"
    _description = "VIES line for Analysis in Bulgarian Localization"
    _auto = False
    _order = "company_id asc"

    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
    )

    info_tag_vir_1 = fields.Char("[VDR-1] Main Record Section Code", readonly=True)
    info_tag_vir_2 = fields.Integer(string="Counter", readonly=True)
    info_tag_vir_3 = fields.Char(
        "[VDR-1] VIN ",
        help="Number of the foreign counterparty incl. " "the sign of the Member State",
        readonly=True,
    )
    info_tag_vir_7 = fields.Char(string="[02-01] Tax period", readonly=True)
    account_tag_vir_4 = fields.Monetary(
        string="[02-15] Base ICD of goods 0%",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_vir_5 = fields.Monetary(
        string="[02-25] TO-trilateral operations",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_vir_6 = fields.Monetary(
        readonly=True,
        string="[02-17] Base under Art. 21 on the territory of the EU",
        currency_field="company_currency_id",
    )

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
    'VDR' AS info_tag_vir_1,
    to_char(am.date, 'YYYYMM') AS info_tag_vir_7,
    am.partner_shipping_id AS partner_id,
    am.state AS state,
    ROW_NUMBER() OVER(ORDER BY am.partner_shipping_id) AS info_tag_vir_2,
    COALESCE(partner.vat, partner.l10n_bg_uic) AS info_tag_vir_3,
    SUM(CASE WHEN aat.tag_name = 15 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 15 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_vir_4,
    SUM(CASE WHEN aat.tag_name = 25 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 25 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_vir_5,
    SUM(CASE WHEN aat.tag_name = 17 AND aat.negate THEN ABS(aml.balance)*-1
            WHEN aat.tag_name = 17 AND NOT aat.negate THEN ABS(aml.balance)
            ELSE 0.00 END) AS account_tag_vir_6"""

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
        ON imd_tag_tax.res_id = aat.id
    LEFT JOIN res_partner AS partner
        ON am.partner_shipping_id = partner.id"""

    @api.model
    def _where(self):
        if self._context.get("report_options"):
            # report_options = self._context.get('report_options')
            # date_from = report_options['date']['date_from']
            # date_to = report_options['date']['date_to']
            # company_id = self.env.company.id
            # unposted_in_period = report_options['unposted_in_period']
            # state = ['posted']
            # if unposted_in_period:
            #     state.append('draft')
            date_from, date_to, tax_period, company_id, state = l10n_bg_where(
                self.env, self._context.get("report_options")
            )
            return f"""am.company_id = {company_id} AND am.state = ANY(ARRAY{state}) AND aat.l10n_bg_applicability = 'sale' AND aat.tag_name = ANY(ARRAY[15, 25, 17]) AND aml.balance != 0 AND am.date >= '{date_from}' AND am.date <= '{date_to}'"""
        return """aat.l10n_bg_applicability = 'sale' AND aat.tag_name = ANY(ARRAY[15,25,17]) AND aml.balance != 0"""

    @api.model
    def _group(self):
        return """am.company_id, info_tag_vir_7, am.partner_shipping_id, am.state, info_tag_vir_3"""
