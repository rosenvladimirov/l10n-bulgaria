# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from psycopg2 import sql

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class AccountBGResultDeclar(models.Model):
    """Base model for new Bulgarian VAT reports."""

    _name = "account.bg.vat.result.declar"
    _description = "VAT Declarations for result for period in Bulgarian Localization"
    _auto = False
    _order = "move_id asc"

    company_id = fields.Many2one(
        "res.company", "Company", readonly=True, auto_join=True
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )
    move_id = fields.Many2one("account.move", string="Account Move", readonly=True)
    account_tag_50 = fields.Monetary(
        string="[01-50] VAT to pay", currency_field="company_currency_id", readonly=True
    )
    account_tag_60 = fields.Monetary(
        string="[01-60] VAT recovery",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_70 = fields.Monetary(
        string="[01-70] Tax for pay from cell[50], deducted in accordance with art. 92, para. 1 VAT",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_71 = fields.Monetary(
        string="[01-71] Tax for pay of cell[50], effectively imported",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_80 = fields.Monetary(
        string="[01-80] Pursuant to Art. 92, Para. 1 VAT within 30 days from the submission of this declaration",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_81 = fields.Monetary(
        string="[01-81] Pursuant to Art. 92, Para. 3 VAT within 30 days from the submission of this declaration",
        currency_field="company_currency_id",
        readonly=True,
    )
    account_tag_82 = fields.Monetary(
        string="[01-82] Pursuant to Art. 92, para. 4 VAT within 30 days from the submission of this declaration",
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
    am.id AS move_id,
    am.date,
    SUM(CASE WHEN aat.tag_name = 50 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 50 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_50,
    SUM(CASE WHEN aat.tag_name = 60 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 60 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_60,
    SUM(CASE WHEN aat.tag_name = 70 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 70 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_70,
    SUM(CASE WHEN aat.tag_name = 71 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 71 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_71,
    SUM(CASE WHEN aat.tag_name = 80 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 80 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_80,
    SUM(CASE WHEN aat.tag_name = 81 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 81 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_81,
    SUM(CASE WHEN aat.tag_name = 82 AND aat.negate THEN ABS(aml.balance)*-1
        WHEN aat.tag_name = 82 AND NOT aat.negate THEN ABS(aml.balance)
        ELSE 0.00 END) AS account_tag_82"""

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
        return """aat.l10n_bg_applicability = 'declaration'"""

    @api.model
    def _group(self):
        return """am.company_id, am.id, am.date"""
