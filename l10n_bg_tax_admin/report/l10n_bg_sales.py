#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class BGVatSaleReport(models.Model):
    _name = 'bg.vat.sale.report'
    _inherit = 'account.form.base.report'

    # ---------------
    # Group by fields
    # ---------------
    move_id = fields.Many2one('account.move',
                              'Account move',
                              readonly=True)

    # -----------
    # Data fields
    # -----------
    tag_02_00 = fields.Char("[02-00] VAT identification number",
                            readonly=True,
                            help="VAT identification number of the company")
    tag_02_01 = fields.Char("[02-01] Tax period",
                            readonly=True,
                            help="Tax period")
    tag_02_02 = fields.Integer("[02-02] Office",
                               readonly=True,
                               help="Office/detached unit")
    tag_02_03 = fields.Integer("[02-03] Number by order",
                               readonly=True,
                               help="Serial number of the document in the journal")
    tag_02_04 = fields.Char("[02-04] Type of document",
                            readonly=True,
                            help="Type of document")
    tag_02_05 = fields.Char("[02-05] Document number",
                            readonly=True,
                            help="Document number")
    tag_02_06 = fields.Date("[02-06] Document date",
                            readonly=True,
                            help="Document date")
    tag_02_07 = fields.Char("[02-07] The identification number of the partner",
                            readonly=True,
                            help="Identification number of the partner (recipient)")
    tag_02_08 = fields.Char("[02-08] Name of partner",
                            readonly=True,
                            help="Name of partner (recipient)")
    tag_02_09 = fields.Char("[02-09] Product type",
                            readonly=True,
                            help="Type of goods or scope and type of service - "
                                 "exact description according to the document")
    tag_02_10 = fields.Float("[02-10] Tax base - Total amount for taxation",
                             readonly=True,
                             help="Total amount of tax bases for VAT taxation")
    tag_02_20 = fields.Float("[02-20] VAT-All charged",
                             readonly=True,
                             help="All VAT charged")
    tag_02_11 = fields.Float("[02-11] Tax base - to be taxed at 20%",
                             readonly=True,
                             help="Tax base of taxable supplies at a rate of 20%, incl. deliveries "
                                  "under the conditions of distance sales, with a place of performance "
                                  "on the territory of the country")
    tag_02_21 = fields.Float("[02-21] VAT-20%",
                             readonly=True,
                             help="Charged VAT 20%")
    tag_02_12 = fields.Float("[02-12] Tax base - Intra-Community arrivals",
                             readonly=True,
                             help="Tax base - Intra-Community arrivals")
    tag_02_26 = fields.Float("[02-26] Tax base - Art. 82, Para. 2-5",
                             readonly=True,
                             help="Tax basis for the received supplies under Art. 82, para. 2 - 5 Law of VAT")
    tag_02_22 = fields.Float("[02-22] VAT - Article 82, Paragraphs 2-5",
                             readonly=True,
                             help="Charged VAT for Intra-Community arrivals and for received supplies under Art. 82, para. 2 - 5 Law of VAT")
    tag_02_23 = fields.Float("[02-23] VAT-personal needs",
                             readonly=True,
                             help="Charged tax for supplies of goods and services for personal needs")
    tag_02_13 = fields.Float("[02-13] Tax base - for taxation at 9%",
                             readonly=True,
                             help="Tax base of taxable supplies at a rate of 9%")
    tag_02_24 = fields.Float("[02-24] VAT-9% tourist services",
                             readonly=True,
                             help="Charged VAT 9%")
    tag_02_14 = fields.Float("[02-14] Tax base - export 0%",
                             readonly=True,
                             help="Tax base of supplies at a rate of 0% under chapter three of Law of VAT")
    tag_02_15 = fields.Float("[02-15] Tax base-VAT 0%",
                             readonly=True,
                             help="Tax base of supplies with a rate of 0% of VAT on goods")
    tag_02_16 = fields.Float("[02-16] Tax base - Art. 140, 146, 173",
                             readonly=True,
                             help="Tax base of supplies at a rate of 0% under Art. 140, "
                                  "Art. 146, para. 1 and Art. 173 Law of VAT")
    tag_02_17 = fields.Float("[02-17] Tax basis - Services under Art. 21, para. 2",
                             readonly=True,
                             help="Tax base of supplies of services under Art. 21, "
                                  "para. 2 VAT, with a place of performance on the territory of another member state")
    tag_02_18 = fields.Float("[02-18] Tax base - distance sales",
                             readonly=True,
                             help="Tax basis of supplies under Art. 69, para. 2 Law of VAT, "
                                  "incl. tax basis of supplies under the conditions of distance sales, "
                                  "with a place of performance in the territory of another member state")
    tag_02_19 = fields.Float("[02-19] Tax base-exempt delivery and Intra-Community arrivals",
                             readonly=True,
                             help="Tax base of exempted supplies and exempted VAT")
    tag_02_25 = fields.Float("[02-25] Tax base - tripartite operation",
                             readonly=True,
                             help="Tax basis of supplies as an intermediary in tripartite transactions")
    tag_02_27 = fields.Char("[02-27] Delivery art. 163a", readonly=True,
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
        query += ' sale_tags AS '
        return query
