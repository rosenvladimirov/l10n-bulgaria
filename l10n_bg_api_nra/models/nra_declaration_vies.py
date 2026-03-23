import logging

from lxml import etree

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

VIES_OPERATION_TYPES = [
    ("supplies", "Доставки на стоки (Supply of goods)"),
    ("services", "Доставки на услуги (Supply of services)"),
    ("triangular", "Тристранни операции (Triangular operations)"),
]


class NraDeclarationViesLine(models.Model):
    _name = "nra.declaration.vies.line"
    _description = "VIES Declaration Line"
    _order = "sequence, id"

    declaration_id = fields.Many2one(
        "nra.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)

    # Partner data
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
    )
    partner_vat = fields.Char(
        string="Partner VAT (ДДС номер на контрагент)",
        required=True,
        size=15,
    )
    partner_country_code = fields.Char(
        string="Country Code",
        size=2,
        required=True,
    )
    partner_name = fields.Char(
        string="Partner Name",
    )

    # Operation data
    operation_type = fields.Selection(
        selection=VIES_OPERATION_TYPES,
        string="Operation Type (Вид операция)",
        required=True,
    )
    tax_base = fields.Float(
        string="Tax Base (Данъчна основа)",
        digits=(12, 2),
        required=True,
    )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and self.partner_id.vat:
            vat = self.partner_id.vat
            self.partner_country_code = vat[:2]
            self.partner_vat = vat
            self.partner_name = self.partner_id.name


class NraDeclarationVies(models.Model):
    _inherit = "nra.declaration"

    vies_line_ids = fields.One2many(
        "nra.declaration.vies.line",
        "declaration_id",
        string="VIES Lines (Редове VIES)",
        states={"draft": [("readonly", False)]},
    )
    vies_line_count = fields.Integer(
        compute="_compute_vies_line_count",
        string="Line Count",
    )

    # Totals
    vies_total_supplies = fields.Float(
        string="Total Supplies (Общо доставки на стоки)",
        digits=(12, 2),
        compute="_compute_vies_totals",
        store=True,
    )
    vies_total_services = fields.Float(
        string="Total Services (Общо доставки на услуги)",
        digits=(12, 2),
        compute="_compute_vies_totals",
        store=True,
    )
    vies_total_triangular = fields.Float(
        string="Total Triangular (Общо тристранни)",
        digits=(12, 2),
        compute="_compute_vies_totals",
        store=True,
    )

    vies_correction_type = fields.Selection(
        selection=[
            ("0", "Редовна (Regular)"),
            ("1", "Коригираща (Correction)"),
        ],
        string="Correction Type",
        default="0",
        states={"draft": [("readonly", False)]},
    )

    @api.depends("vies_line_ids")
    def _compute_vies_line_count(self):
        for rec in self:
            rec.vies_line_count = len(rec.vies_line_ids)

    @api.depends("vies_line_ids.tax_base", "vies_line_ids.operation_type")
    def _compute_vies_totals(self):
        for rec in self:
            rec.vies_total_supplies = sum(
                line.tax_base
                for line in rec.vies_line_ids
                if line.operation_type == "supplies"
            )
            rec.vies_total_services = sum(
                line.tax_base
                for line in rec.vies_line_ids
                if line.operation_type == "services"
            )
            rec.vies_total_triangular = sum(
                line.tax_base
                for line in rec.vies_line_ids
                if line.operation_type == "triangular"
            )

    def _prepare_xml_data(self):
        self.ensure_one()
        if self.declaration_type != "vies":
            return super()._prepare_xml_data()
        return {
            "eik": self.l10n_bg_uic,
            "month": self.period_month,
            "year": self.period_year,
            "correction_type": self.vies_correction_type,
            "total_supplies": self.vies_total_supplies,
            "total_services": self.vies_total_services,
            "total_triangular": self.vies_total_triangular,
            "lines": [
                {
                    "partner_vat": line.partner_vat,
                    "partner_country_code": line.partner_country_code,
                    "partner_name": line.partner_name,
                    "operation_type": line.operation_type,
                    "tax_base": line.tax_base,
                }
                for line in self.vies_line_ids
            ],
        }

    def _build_xml_tree(self, data):
        self.ensure_one()
        if self.declaration_type != "vies":
            return super()._build_xml_tree(data)

        root = etree.Element("VIESDeclaration")
        header = etree.SubElement(root, "Header")
        etree.SubElement(header, "EIK").text = data["eik"]
        etree.SubElement(header, "Month").text = str(data["month"])
        etree.SubElement(header, "Year").text = str(data["year"])
        etree.SubElement(header, "CorrectionType").text = data["correction_type"]

        summary = etree.SubElement(root, "Summary")
        etree.SubElement(summary, "TotalSupplies").text = f"{data['total_supplies']:.2f}"
        etree.SubElement(summary, "TotalServices").text = f"{data['total_services']:.2f}"
        etree.SubElement(summary, "TotalTriangular").text = f"{data['total_triangular']:.2f}"

        records = etree.SubElement(root, "Records")
        for line_data in data.get("lines", []):
            record = etree.SubElement(records, "Record")
            etree.SubElement(record, "PartnerCountryCode").text = line_data[
                "partner_country_code"
            ]
            etree.SubElement(record, "PartnerVAT").text = line_data["partner_vat"]
            if line_data.get("partner_name"):
                etree.SubElement(record, "PartnerName").text = line_data["partner_name"]
            etree.SubElement(record, "OperationType").text = line_data["operation_type"]
            etree.SubElement(record, "TaxBase").text = f"{line_data['tax_base']:.2f}"

        return root
