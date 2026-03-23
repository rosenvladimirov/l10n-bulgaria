import logging

from lxml import etree

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class NraDeclarationVatLine(models.Model):
    _name = "nra.declaration.vat.line"
    _description = "VAT Declaration Line"
    _order = "sequence, id"

    declaration_id = fields.Many2one(
        "nra.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)

    cell_number = fields.Char(
        string="Cell (Клетка)",
        required=True,
    )
    description = fields.Char(
        string="Description (Описание)",
    )
    amount = fields.Float(
        string="Amount (Сума)",
        digits=(12, 2),
        required=True,
    )


class NraDeclarationVat(models.Model):
    _inherit = "nra.declaration"

    # ------------------------------------------------------------------
    # VAT Declaration header fields
    # ------------------------------------------------------------------

    vat_line_ids = fields.One2many(
        "nra.declaration.vat.line",
        "declaration_id",
        string="VAT Lines (Клетки)",
        states={"draft": [("readonly", False)]},
    )
    vat_line_count = fields.Integer(
        compute="_compute_vat_line_count",
        string="Line Count",
    )

    # Summary amounts
    vat_total_sales = fields.Float(
        string="Total Sales (Общо продажби)",
        digits=(12, 2),
        states={"draft": [("readonly", False)]},
    )
    vat_total_purchases = fields.Float(
        string="Total Purchases (Общо покупки)",
        digits=(12, 2),
        states={"draft": [("readonly", False)]},
    )
    vat_charged = fields.Float(
        string="VAT Charged (Начислен ДДС)",
        digits=(12, 2),
        states={"draft": [("readonly", False)]},
    )
    vat_credit = fields.Float(
        string="VAT Credit (Данъчен кредит)",
        digits=(12, 2),
        states={"draft": [("readonly", False)]},
    )
    vat_due = fields.Float(
        string="VAT Due (ДДС за внасяне)",
        digits=(12, 2),
        compute="_compute_vat_due",
        store=True,
    )
    vat_refund = fields.Float(
        string="VAT Refund (ДДС за възстановяване)",
        digits=(12, 2),
        compute="_compute_vat_due",
        store=True,
    )

    # Correction
    vat_correction_type = fields.Selection(
        selection=[
            ("0", "Редовна (Regular)"),
            ("1", "Коригираща (Correction)"),
        ],
        string="Correction Type",
        default="0",
        states={"draft": [("readonly", False)]},
    )

    @api.depends("vat_line_ids")
    def _compute_vat_line_count(self):
        for rec in self:
            rec.vat_line_count = len(rec.vat_line_ids)

    @api.depends("vat_charged", "vat_credit")
    def _compute_vat_due(self):
        for rec in self:
            diff = rec.vat_charged - rec.vat_credit
            if diff > 0:
                rec.vat_due = diff
                rec.vat_refund = 0.0
            else:
                rec.vat_due = 0.0
                rec.vat_refund = abs(diff)

    def _prepare_xml_data(self):
        self.ensure_one()
        if self.declaration_type != "vat":
            return super()._prepare_xml_data()
        return {
            "eik": self.l10n_bg_uic,
            "month": self.period_month,
            "year": self.period_year,
            "correction_type": self.vat_correction_type,
            "total_sales": self.vat_total_sales,
            "total_purchases": self.vat_total_purchases,
            "vat_charged": self.vat_charged,
            "vat_credit": self.vat_credit,
            "vat_due": self.vat_due,
            "vat_refund": self.vat_refund,
            "lines": [
                {
                    "cell_number": line.cell_number,
                    "description": line.description,
                    "amount": line.amount,
                }
                for line in self.vat_line_ids
            ],
        }

    def _build_xml_tree(self, data):
        self.ensure_one()
        if self.declaration_type != "vat":
            return super()._build_xml_tree(data)

        root = etree.Element("VATDeclaration")
        header = etree.SubElement(root, "Header")
        etree.SubElement(header, "EIK").text = data["eik"]
        etree.SubElement(header, "Month").text = str(data["month"])
        etree.SubElement(header, "Year").text = str(data["year"])
        etree.SubElement(header, "CorrectionType").text = data["correction_type"]

        summary = etree.SubElement(root, "Summary")
        etree.SubElement(summary, "TotalSales").text = f"{data['total_sales']:.2f}"
        etree.SubElement(summary, "TotalPurchases").text = f"{data['total_purchases']:.2f}"
        etree.SubElement(summary, "VATCharged").text = f"{data['vat_charged']:.2f}"
        etree.SubElement(summary, "VATCredit").text = f"{data['vat_credit']:.2f}"
        etree.SubElement(summary, "VATDue").text = f"{data['vat_due']:.2f}"
        etree.SubElement(summary, "VATRefund").text = f"{data['vat_refund']:.2f}"

        cells = etree.SubElement(root, "Cells")
        for line_data in data.get("lines", []):
            cell = etree.SubElement(cells, "Cell")
            etree.SubElement(cell, "Number").text = line_data["cell_number"]
            if line_data.get("description"):
                etree.SubElement(cell, "Description").text = line_data["description"]
            etree.SubElement(cell, "Amount").text = f"{line_data['amount']:.2f}"

        return root
