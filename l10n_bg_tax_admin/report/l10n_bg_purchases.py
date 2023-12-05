#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.account_financial_forms.report.account_form_base_report import MODELS


class BGVatPurchaseReport(models.Model):
    _name = 'bg.vat.purchase.report'
    _inherit = 'account.form.base.report'

    move_id = fields.Many2one('account.move', 'Account move',
                              readonly=True)

    tag_03_01 = fields.Char("[03-01] Tax period",
                            readonly=True,
                            help="Report tax period")
    tag_03_02 = fields.Char("[03-02] VAT Company",
                            readonly=True,
                            help="VAT identification number of the company")
    tag_03_03 = fields.Integer("[03-03] Office",
                               readonly=True,
                               help="Office/detached unit")
    tag_03_04 = fields.Integer("[03-04] Number by order",
                               readonly=True,
                               help="Serial number of the document in the journal")
    tag_03_05 = fields.Char("[03-05] Type of document",
                            readonly=True,
                            help="Type of original document")
    tag_03_06 = fields.Char("[03-06] Document number",
                            readonly=True,
                            help="Number of original document")
    tag_03_07 = fields.Date("[03-07] Document date",
                            readonly=True,
                            help="Date of original document")
    tag_03_08 = fields.Char("[03-08] ID of the partner",
                            readonly=True,
                            help="Identification number of the partner (supplier)")
    tag_03_09 = fields.Char("[03-09] Name of partner",
                            readonly=True,
                            help="Name of partner (supplier)")
    tag_03_10 = fields.Char("[03-10] Product type",
                            readonly=True,
                            help="Type of goods or scope and type of service "
                                 "- exact description according to the document")
    tag_03_12 = fields.Float("[03-12] Tax base of supplies received",
                             readonly=True,
                             help="Tax base of received supplies, VAT, "
                                  "the received supplies under Art. 82, para. 2 - 5 VAT, "
                                  "the import, as well as the tax base of the supplies received, "
                                  "used to make deliveries under Art. 69, "
                                  "para. 2 VAT with the right to a partial tax credit.")
    tag_03_11 = fields.Float("[03-11] VAT with the right to a full tax credit",
                             readonly=True,
                             help="Charged VAT 20% with the right to use the full tax credit")
    tag_03_13 = fields.Float("[03-13] VAT with the right to a partial tax credit",
                             readonly=True,
                             help="Charged VAT 20% with the right to use a partial tax credit")
    tag_03_14 = fields.Float("[03-14] Annual adjustment",
                             readonly=True,
                             help="Annual adjustment under Art. 73, para. 8 VAT")
    tag_03_15 = fields.Float("[03-15] Trilateral operation",
                             readonly=True,
                             help="Tax base when acquiring goods from an intermediary in a tripartite transaction")
    tag_03_30 = fields.Float("[03-30] Tax basis - no right to tax credit",
                             readonly=True,
                             help="Tax base and tax on supplies received, "
                                  "Intra community imports, the received supplies under Art. 82, "
                                  "para. 2 - 5 Law of VAT and the importation without the right "
                                  "to tax credit or without tax")
    tag_03_31 = fields.Float("[03-31] Tax basis - full tax credit",
                             readonly=True,
                             help="Tax basis of supplies received, "
                                  "Intra community imports, the received supplies under Art. 82, para. 2 - 5 VAT, "
                                  "the import, as well as the tax base of the supplies received, "
                                  "used to make deliveries under Art. 69, "
                                  "para. 2 Law of VAT with the right to a full tax credit")
    tag_03_41 = fields.Float("[03-41] VAT - full tax credit",
                             readonly=True,
                             help="VAT with the right to a full tax credit")
    tag_03_32 = fields.Float("[03-32] Tax base - partial tax credit",
                             readonly=True,
                             help="Tax base of supplies received, "
                                  "Intra community imports, the received supplies under Art. 82, para. 2 - 5 VAT, "
                                  "the import, as well as the tax base of the supplies received, "
                                  "used to make deliveries under Art. 69, "
                                  "para. 2 Law of VAT with the right to a partial tax credit")
    tag_03_42 = fields.Float("[03-42] VAT-partial tax credit",
                             readonly=True,
                             help="VAT with the right to a partial tax credit")
    tag_03_43 = fields.Float("[03-43] Annual adjustment - art. 73, paragraph 8",
                             readonly=True,
                             help="Annual adjustment under Art. 73, para. 8 Law of VAT")
    tag_03_44 = fields.Float("[03-44] Tax base tripartite operation",
                             readonly=True,
                             help="Tax base when acquiring goods from an intermediary in a tripartite transaction")
    tag_03_45 = fields.Char("[03-45] Trilateral operation",
                            readonly=True,
                            help="Tax basis when acquiring goods from an intermediary in a tripartite transaction")
    tag_03_80 = fields.Char("[03-8а] Tax base - art. 163a",
                            readonly=True,
                            help="Delivery according to Art. 163a of the Law of VAT")

    def _select_domain_type(self, form_id):
        if form_id.account_forms == 'vat_form':
            domain_type = """ANY({'in_invoice', 'in_refund', 'in_receipt'}::text[])"""
        else:
            domain_type = "'entry'"
        return domain_type

    def _group_by(self, date_to, date_from=False, form_id=False, date_range_fm_id=False):
        query = super()._group_by(date_to, date_from=date_from, form_id=form_id, date_range_fm_id=date_range_fm_id)
        query += """, aml.move_line_id"""
        return query

    def _from(self, form_id=False):
        return """ purchase_tags """

    def _with(self, form_id=False):
        query = super()._with(form_id=form_id)
        query += ' purchase_tags AS '
        return query
