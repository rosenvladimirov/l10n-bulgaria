#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class BGVatViesReport(models.Model):
    _name = 'bg.vat.vies.report'
    _inherit = 'account.form.base.report'

    tag_0501 = fields.Char("[05-01/07-01] Section Code *ICA/Storage Mode*",
                           readonly=True,
                           help="Code of the section *ICA/Transfer of goods under the mode of storage of goods on demand* VIR")
    tag_0502 = fields.Integer("[05-02/07-02] Line number",
                              readonly=True,
                              help="Line number")
    tag_0503 = fields.Char("[05-03] VIN number",
                           readonly=True,
                           help="VIN number of the foreign partner, incl. the sign of the Member State")
    tag_0504 = fields.Float("[05-04] Total value of the tax base",
                            readonly=True,
                            help="Total value of the tax base for supplies of goods")
    tag_0505 = fields.Float("[05-05] Three-way operation",
                            readonly=True,
                            help="Supplies of goods as an intermediary in a tripartite operation")
    tag_0506 = fields.Float("[05-06] Delivered services under Art. 21",
                            readonly=True,
                            help="Total value of the tax base for delivered services under Art. 21, "
                                 "para. 2 of Law of VAT, with place of performance "
                                 "in the territory of another member state")
    tag_0507 = fields.Char("[05-07/07-06] Reporting period",
                           readonly=True,
                           help="Reporting period for the performed VOD to the relevant foreign partner")
    tag_0703 = fields.Char("[07-03] VIN number of recipient person",
                           readonly=True,
                           help="VAT number of the person for whom the goods are intended (including the sign)")
    tag_0704 = fields.Char("[07-04] Operation code",
                           readonly=True,
                           help="Code of the operation under the storage of goods on demand mode")
    tag_0705 = fields.Char("[07-05] VIN number of the person replacement",
                           readonly=True,
                           help="VAT identification number of the person for whom the goods were "
                                "intended for replacement under Art. 15a, para. 4 of VAT (incl. signs)")

    def _select_domain_type(self, form_id):
        if form_id.account_forms == 'vat_form':
            domain_type = """ANY({'out_invoice', 'out_refund', 'out_receipt'}::text[])"""
        else:
            domain_type = "'entry'"
        return domain_type

    def _group_by(self, date_to, date_from=False, form_id=False, date_range_fm_id=False):
        query = super()._group_by(date_to, date_from=date_from, form_id=form_id, date_range_fm_id=date_range_fm_id)
        query += """, aml.partner_id"""
        return query

    def _from(self, form_id=False):
        return """ vies_tags """

    def _with(self, form_id=False):
        query = super()._with(form_id=form_id)
        query += ' vies_tags AS '
        return query
