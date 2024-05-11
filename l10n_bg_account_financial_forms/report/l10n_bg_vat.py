#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BGVatReport(models.Model):
    _name = "bg.vat.report"
    _inherit = "account.form.base.report"

    tag_00_01 = fields.Char(
        "[00-01] VAT identification number",
        readonly=True,
        help="VAT identification number of the taxable company/person",
    )
    # tag_00_01a = fields.Char("[00-01] Identification number",
    #                       help="Identification number of the company/person")
    tag_00_02 = fields.Char(
        "[00-02] Company name", readonly=True, help="Name of the taxable company/person"
    )
    tag_00_02a = fields.Char(
        "[00-02] Company address",
        readonly=True,
        help="Address of the taxable company/person",
    )
    tag_00_03 = fields.Char(
        "[00-03] VAT Period", readonly=True, help="Tax reporting period"
    )
    tag_00_04 = fields.Char(
        "[00-04] Person submitting the declaration - TIN, name",
        readonly=True,
        help="Person submitting the declaration and represent the company - TIN, name",
    )
    tag_00_05 = fields.Integer(
        "[00-05] Number of documents in the sales journal",
        readonly=True,
        help="Number of documents in the sales journal linked with the declaration",
    )
    tag_00_06 = fields.Integer(
        "[00-06] Number of documents in the purchase journal",
        readonly=True,
        help="Number of documents in the purchase journal linked with the declaration",
    )

    # Sales
    tag_01_01 = fields.Float(
        "[01-01] Base sales total",
        readonly=True,
        help="Total amount of tax bases for VAT taxation",
    )
    tag_01_20 = fields.Float(
        "[01-20] VAT taxes of sales total",
        readonly=True,
        help="Total of VAT taxes for sales",
    )
    tag_01_11 = fields.Float(
        "[01-11] Base of taxable sales",
        readonly=True,
        help="Tax base of taxable supplies at a rate of 20% incl. "
        "deliveries under the conditions of distance sales, with place "
        "of execution on the territory of the country.",
    )
    tag_01_21 = fields.Float(
        "[01-21] VAT-sales for taxation", readonly=True, help="Charged VAT with 20%"
    )
    tag_01_12 = fields.Float(
        "[01-12] Tax base - Intra community imports and tax payer when making taxable supplies",
        readonly=True,
        help="Tax base of Intra community imports and tax base "
        "of received supplies under Art. 82, para. 2 - 5 VAT",
    )
    tag_01_22 = fields.Float(
        "[01-22] VAT-Intra community imports and tax payer when making taxable supplies",
        readonly=True,
        help="Charged tax for Intra community imports and "
        "for received supplies under Art. 82, para. 2 - 5 VAT",
    )
    tag_01_23 = fields.Float(
        "[01-23] VAT-Personal needs",
        readonly=True,
        help="Charged tax for supplies of goods and services for personal needs",
    )
    tag_01_13 = fields.Float(
        "[01-13] Tax base - sales of tourist services",
        readonly=True,
        help="Tax base of taxable supplies at a rate of 9%",
    )
    tag_01_24 = fields.Float(
        "[01-24] VAT-sales of tourist services", readonly=True, help="Charged VAT 9%"
    )
    tag_01_14 = fields.Float(
        "[01-14] Tax base - export sales",
        readonly=True,
        help="Tax base subject to taxation at a rate of 0% under chapter three of VAT",
    )
    tag_01_15 = fields.Float(
        "[01-15] Tax base-sales Intra community exports",
        readonly=True,
        help="Tax base, on supplies at a rate of 0% for Intra community exports goods",
    )
    tag_01_16 = fields.Float(
        "[01-16] Tax base-sales tourist service",
        readonly=True,
        help="Tax base of supplies subject to 0% tax under Art. 140, 146 and Art. 173 VAT, "
        "the special order of taxing the margin with a zero rate, by virtue of international treaties",
    )
    tag_01_17 = fields.Float(
        "[01-17] Tax base - sales within the EU",
        readonly=True,
        help="Tax base of supplies of services under Art. 21, "
        "para. 2 VAT with a place of performance on the territory of another member EU",
    )
    tag_01_18 = fields.Float(
        "[01-18] Tax base - sales under Art. 62(2) on the territory of the EU",
        readonly=True,
        help="Tax basis of supplies under Art. 69, para. 2 Law of VAT, "
        "incl. deliveries under the conditions of distance sales, "
        "with a place of performance on the territory of another member EU",
    )
    tag_01_19 = fields.Float(
        "[01-19] Tax base-sales exempt from Intra community exports",
        readonly=True,
        help="Tax base of exempted supplies and exempted Intra community exports",
    )

    # Purchase
    tag_01_30 = fields.Float(
        "[01-30] Tax base - purchases without the right to a tax credit",
        readonly=True,
        help="Tax base and tax on received supplies, VAT, "
        "received supplies under Art. 82, para. 2 - 5 Law of VAT "
        "and the importation without the right to tax credit or without tax",
    )
    tag_01_31 = fields.Float(
        "[01-31] Tax basis - purchases entitled to a full tax credit",
        readonly=True,
        help="Tax basis of received supplies, Intra community exports, "
        "received supplies under Art. 82, para. 2 - 5 Law of VAT, "
        "the import, as well as the tax basis of the received supplies, "
        "used to make supplies under Art. 69, para. 2 Law of VAT "
        "with the right to a full tax credit",
    )
    tag_01_41 = fields.Float(
        "[01-41] VAT - purchases full tax credit",
        readonly=True,
        help="Charged VAT with the right to a full tax credit",
    )
    tag_01_32 = fields.Float(
        "[01-32] Tax base - purchases with partial tax credit (~%)",
        readonly=True,
        help="Tax basis of received supplies, Intra community exports, "
        "received supplies under Art. 82, para. 2 - 5 Law of VAT, "
        "the import, as well as the tax basis of the received supplies, "
        "used to make supplies under Art. 69, para. 2 Law of VAT "
        "with the right to a partial tax credit",
    )
    tag_01_42 = fields.Float(
        "[01-42] VAT - purchases with partial tax credit (~%)",
        readonly=True,
        help="Charged VAT with the right to a partial tax credit",
    )

    # Totals
    tag_01_43 = fields.Float(
        "[01-43] Correction of art. 73, paragraph 8",
        readonly=True,
        help="Annual adjustment under Art. 73, para. 8 (+/-) Law of VAT",
    )
    tag_01_33 = fields.Float(
        "[01-33] Coefficient art. 73, paragraph 5",
        readonly=True,
        help="Coefficient under Art. 73, para. 5 Law of VAT",
    )
    tag_01_40 = fields.Float(
        "[01-40] VAT - purchases",
        readonly=True,
        help="Total tax credit (cl. 41 + cl. 42 x cl. 33 + cl. 43)",
    )
    tag_01_50 = fields.Float(
        "[01-50] VAT to pay", readonly=True, help="Import VAT (cl. 20 - cl. 40) >= 0"
    )
    tag_01_60 = fields.Float(
        "[01-60] VAT recovery", readonly=True, help="VAT refund (cl. 20 - cl. 40) < 0"
    )
    tag_01_70 = fields.Float(
        "[01-70] VAT-deducted art. 92, paragraph 1",
        readonly=True,
        help="Import tax from Article 50, deducted in accordance with Art. 92, para. 1 Law of VAT",
    )
    tag_01_71 = fields.Float(
        "[01-71] VAT-filed effectively",
        readonly=True,
        help="Input tax from cl. 50, effectively input",
    )
    tag_01_80 = fields.Float(
        "[01-80] VAT-reimbursement Art. 92, paragraph 1",
        readonly=True,
        help="VAT subject to refund, according to Art. 92, para. 1 "
        "Law of VAT within 30 days of submitting this declaration",
    )
    tag_01_81 = fields.Float(
        "[01-81] VAT-reimbursement Art. 92, paragraph 3",
        help="VAT subject to refund, according to Art. 92, para. 3 "
        "Law of VAT within 30 days of submitting this declaration",
    )
    tag_01_82 = fields.Float(
        "[01-82] VAT-for refund, Art. 92, para. 4",
        help="VAT subject to refund, according to Art. 92, para. 4 Law of VAT "
        "within 30 days from the submission of this declaration",
    )

    def _select_domain_type(self, form_id):
        if form_id.account_forms == "vat_form":
            domain_type = """ANY({'in_invoice', 'in_refund', 'in_receipt', 'out_invoice', 'out_refund', 'out_receipt'}::text[])"""
        else:
            domain_type = "'entry'"
        return domain_type

    def _group_by(
        self, date_to, date_from=False, form_id=False, date_range_fm_id=False
    ):
        query = super()._group_by(
            date_to,
            date_from=date_from,
            form_id=form_id,
            date_range_fm_id=date_range_fm_id,
        )
        query += """, aml.move_id"""
        return query

    def _from(self, form_id=False):
        return """ vat_tags """

    def _with(self, form_id=False):
        query = super()._with(form_id=form_id)
        query += " vat_tags AS "
        return query
