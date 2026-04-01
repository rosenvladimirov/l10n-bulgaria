import logging

from lxml import etree

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

D6_CONTRIBUTION_TYPES = [
    ("1", "1 — Дължими вноски за месеца"),
    ("2", "2 — Еднократни суми"),
    ("3", "3 — Самоосигуряващи се лица"),
    ("4", "4 — Годишно изравняване"),
    ("5", "5 — Неразпределена печалба"),
]


class NraDeclarationD6Line(models.Model):
    _name = "nra.declaration.d6.line"
    _description = "Declaration Form 6 — Contribution Line"
    _order = "sequence, id"

    declaration_id = fields.Many2one(
        "nra.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)

    contribution_type = fields.Selection(
        selection=D6_CONTRIBUTION_TYPES,
        string="Contribution Type (Вид плащане)",
        required=True,
    )
    payment_month = fields.Selection(
        selection=[
            ("1", "01"), ("2", "02"), ("3", "03"), ("4", "04"),
            ("5", "05"), ("6", "06"), ("7", "07"), ("8", "08"),
            ("9", "09"), ("10", "10"), ("11", "11"), ("12", "12"),
            ("13", "13"),
        ],
        string="Payment Month",
        required=True,
    )
    payment_year = fields.Char(
        string="Payment Year",
        size=4,
        required=True,
    )

    # Contributions
    doo_amount = fields.Float(
        string="DOO (Фонд Пенсии)",
        digits=(12, 2),
    )
    teachers_fund = fields.Float(
        string="Teachers Fund (УчПФ)",
        digits=(12, 2),
    )
    dzpo_upf = fields.Float(
        string="DZPO — UPF (ДЗПО-УПФ)",
        digits=(12, 2),
    )
    dzpo_ppf = fields.Float(
        string="DZPO — PPF (ДЗПО-ППФ)",
        digits=(12, 2),
    )
    health_insurance = fields.Float(
        string="Health Insurance (ЗО)",
        digits=(12, 2),
    )
    income_tax = fields.Float(
        string="Income Tax (ДДФЛ)",
        digits=(12, 2),
    )
    total_amount = fields.Float(
        string="Total",
        compute="_compute_total_amount",
        digits=(12, 2),
        store=True,
    )

    @api.depends(
        "doo_amount",
        "teachers_fund",
        "dzpo_upf",
        "dzpo_ppf",
        "health_insurance",
        "income_tax",
    )
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = (
                line.doo_amount
                + line.teachers_fund
                + line.dzpo_upf
                + line.dzpo_ppf
                + line.health_insurance
                + line.income_tax
            )


class NraDeclarationD6(models.Model):
    _inherit = "nra.declaration"

    d6_line_ids = fields.One2many(
        "nra.declaration.d6.line",
        "declaration_id",
        string="Contribution Lines (Вноски)",
    )
    d6_line_count = fields.Integer(
        compute="_compute_d6_line_count",
        string="Line Count",
    )
    d6_correction_type = fields.Selection(
        selection=[
            ("0", "Редовна (Regular)"),
            ("1", "Коригираща (Correction)"),
            ("2", "Заличаваща (Deletion)"),
        ],
        string="Correction Type",
        default="0",
    )
    d6_payment_date = fields.Date(
        string="Payment Date (Дата на плащане/изплащане)",
    )

    @api.depends("d6_line_ids")
    def _compute_d6_line_count(self):
        for rec in self:
            rec.d6_line_count = len(rec.d6_line_ids)

    def _prepare_xml_data(self):
        self.ensure_one()
        if self.declaration_type != "d6":
            return super()._prepare_xml_data()
        return {
            "eik": self.l10n_bg_uic,
            "month": self.period_month,
            "year": self.period_year,
            "correction_type": self.d6_correction_type,
            "payment_date": self.d6_payment_date
            and self.d6_payment_date.strftime("%Y-%m-%d"),
            "lines": [
                {
                    "contribution_type": line.contribution_type,
                    "payment_month": line.payment_month,
                    "payment_year": line.payment_year,
                    "doo_amount": line.doo_amount,
                    "teachers_fund": line.teachers_fund,
                    "dzpo_upf": line.dzpo_upf,
                    "dzpo_ppf": line.dzpo_ppf,
                    "health_insurance": line.health_insurance,
                    "income_tax": line.income_tax,
                }
                for line in self.d6_line_ids
            ],
        }

    def _build_xml_tree(self, data):
        self.ensure_one()
        if self.declaration_type != "d6":
            return super()._build_xml_tree(data)

        root = etree.Element("Declaration", type="D6")
        header = etree.SubElement(root, "Header")
        etree.SubElement(header, "EIK").text = data["eik"]
        etree.SubElement(header, "Month").text = str(data["month"])
        etree.SubElement(header, "Year").text = str(data["year"])
        etree.SubElement(header, "CorrectionType").text = data["correction_type"]
        if data.get("payment_date"):
            etree.SubElement(header, "PaymentDate").text = data["payment_date"]

        records = etree.SubElement(root, "Records")
        for line_data in data.get("lines", []):
            record = etree.SubElement(records, "Record")
            etree.SubElement(record, "ContributionType").text = line_data["contribution_type"]
            etree.SubElement(record, "PaymentMonth").text = str(line_data["payment_month"])
            etree.SubElement(record, "PaymentYear").text = str(line_data["payment_year"])
            etree.SubElement(record, "DOOAmount").text = f"{line_data['doo_amount']:.2f}"
            etree.SubElement(record, "TeachersFund").text = f"{line_data['teachers_fund']:.2f}"
            etree.SubElement(record, "DZPOUPF").text = f"{line_data['dzpo_upf']:.2f}"
            etree.SubElement(record, "DZPOPPF").text = f"{line_data['dzpo_ppf']:.2f}"
            etree.SubElement(record, "HealthInsurance").text = f"{line_data['health_insurance']:.2f}"
            etree.SubElement(record, "IncomeTax").text = f"{line_data['income_tax']:.2f}"

        return root
