# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    l10n_bg_extend_address,
    l10n_bg_lang,
    l10n_bg_where,
)

_logger = logging.getLogger(__name__)


class AccountBGInfoViesDeclaration(models.Model):
    _name = "account.bg.vies.info.declar"
    _description = "VIES Declaration for Analysis in Bulgarian Localization"
    _auto = False
    _order = "company_id asc"

    company_id = fields.Many2one("res.company", "Company", readonly=True)
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True
    )

    info_tag_vhr_1 = fields.Char("[VHR-1] Main Record Section Code", readonly=True)
    info_tag_vhr_2 = fields.Char(string="[VHR-2] Tax period", readonly=True)
    info_tag_vhr_3 = fields.Integer(
        string="[VHR-3] Number of documents in the vies journal", readonly=True
    )

    info_tag_vdr_1 = fields.Char("[VDR-1] Main Record Section Code", readonly=True)
    info_tag_vdr_2 = fields.Char(
        "[VDR-2] Represented person UIN",
        help="UIN/UINF/service number from "
        "the NRA register of the person submitting the declaration",
        readonly=True,
    )
    info_tag_vdr_3 = fields.Char("[VDR-3] Represented person name", readonly=True)
    info_tag_vdr_4 = fields.Char("[VDR-4] Represented person city", readonly=True)
    info_tag_vdr_5 = fields.Char("[VDR-5] Represented person ZIP", readonly=True)
    info_tag_vdr_6 = fields.Char("[VDR-6] Represented person address", readonly=True)
    info_tag_vdr_7 = fields.Char("[VDR-7] Represented person function", readonly=True)

    info_tag_vtr_1 = fields.Char("[VDR-1] Main Record Section Code", readonly=True)
    info_tag_vtr_2 = fields.Char("Company UIC", readonly=True)
    info_tag_vtr_3 = fields.Char("Company name", readonly=True)
    info_tag_vtr_4 = fields.Char("Company address", readonly=True)

    info_tag_ttr_1 = fields.Char("[VDR-1] Main Record Section Code", readonly=True)
    account_tag_ttr_2 = fields.Monetary(
        readonly=True,
        string="[TTR-2] Base for ICD total [01-15]",
        currency_field="company_currency_id",
    )
    account_tag_ttr_3 = fields.Monetary(
        readonly=True,
        string="[TTR-2] Base for ICD",
        currency_field="company_currency_id",
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
        'VHR' AS info_tag_vhr_1,
        acc.info_tag_vir_7 AS info_tag_vhr_2,
        'VDR' AS info_tag_vdr_1,
        represent_partner.l10n_bg_uic AS info_tag_vdr_2,
        {l10n_bg_lang(self.env, lang_modules='partner', field_name='represent_partner.name')} AS info_tag_vdr_3,
        {l10n_bg_lang(self.env, lang_modules='partner', field_name='represent_partner.city')} AS info_tag_vdr_4,
        represent_partner.zip AS info_tag_vdr_5,
        {l10n_bg_lang(self.env, lang_modules='partner', field_name='represent_partner.street')} AS info_tag_vdr_6,
        UPPER(SUBSTRING(represent_partner.type FOR 1)) AS info_tag_vdr_7,
        'VTR' AS info_tag_vtr_1,
        COALESCE(company_partner.l10n_bg_uic, company_partner.vat) AS info_tag_vtr_2,
        {l10n_bg_lang(self.env, lang_modules='partner', field_name='company_partner.name')} AS info_tag_vtr_3,
        CONCAT ({l10n_bg_lang(self.env, lang_modules='partner', field_name='company_partner.city')}, ', ', {l10n_bg_lang(self.env, lang_modules='partner', field_name='company_partner.street')}) AS info_tag_vtr_4,
        'TTR' AS info_tag_ttr_1,
        COUNT(acc.partner_id) AS info_tag_vhr_3,
        SUM(acc.account_tag_vir_4 + acc.account_tag_vir_5 + acc.account_tag_vir_6) AS account_tag_ttr_2,
        SUM(acc.account_tag_vir_4) AS account_tag_ttr_3"""

    @api.model
    def _from(self):
        sub_select = (
            self.env["account.bg.calc.vies.line"]
            .with_context(**dict(self.env.context))
            ._table_query
        )
        return f"""({sub_select}) AS acc
LEFT JOIN res_company AS company
    ON acc.company_id = company.id
LEFT JOIN res_partner AS company_partner
    ON company.partner_id = company_partner.id
LEFT JOIN res_partner AS represent_partner
    ON company.l10n_bg_tax_contact_id = represent_partner.id""" + \
            l10n_bg_extend_address(self.env) + l10n_bg_extend_address(self.env, model="represent_partner")

    @api.model
    def _where(self):
        if self.env.context.get("report_options"):
            date_from, date_to, tax_period, tax_periods, company_id, state = l10n_bg_where(
                self.env, self.env.context.get("report_options")
            )
            if len(tax_periods) == 0:
                return f"""acc.company_id = {company_id} AND acc.state = ANY(ARRAY{state}) AND acc.info_tag_vir_7 = '{tax_period}'"""
            else:
                return f"""acc.company_id = {company_id} AND acc.state = ANY(ARRAY{state}) AND acc.info_tag_vir_7 = ANY(ARRAY{tax_periods})"""
        return ""

    @api.model
    def _group(self):
        return """acc.company_id, acc.info_tag_vir_7, info_tag_vdr_2, info_tag_vdr_3, info_tag_vdr_4, info_tag_vdr_5, info_tag_vdr_6, info_tag_vdr_7, info_tag_vtr_2, info_tag_vtr_3, info_tag_vtr_4"""
