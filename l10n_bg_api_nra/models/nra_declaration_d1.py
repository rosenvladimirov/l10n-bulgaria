import logging

from lxml import etree

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

# Insurance types per Bulgarian social security legislation
D1_INSURANCE_TYPES = [
    ("01", "01 — Трудов договор по КТ"),
    ("04", "04 — Управление и контрол на ТД/ЕТ"),
    ("10", "10 — Без трудово правоотношение (граждански договор)"),
    ("12", "12 — Самоосигуряващо се лице"),
    ("14", "14 — Работещ без трудово правоотношение с осигуряване"),
    ("82", "82 — Морски лица"),
    ("90", "90 — Неплатен отпуск/майчинство"),
]


class NraDeclarationD1Line(models.Model):
    _name = "nra.declaration.d1.line"
    _description = "Declaration Form 1 — Insured Person Line"
    _order = "sequence, id"

    declaration_id = fields.Many2one(
        "nra.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)

    # Insured person identification
    egn_lnch = fields.Char(
        string="ЕГН/ЛНЧ",
        required=True,
        size=10,
    )
    person_names = fields.Char(
        string="Names (Имена)",
        required=True,
    )
    id_type = fields.Selection(
        selection=[
            ("0", "ЕГН"),
            ("1", "ЛНЧ"),
            ("2", "Служебен номер"),
        ],
        string="ID Type",
        required=True,
        default="0",
    )

    # Insurance data
    insurance_type = fields.Selection(
        selection=D1_INSURANCE_TYPES,
        string="Insurance Type (Вид осигурен)",
        required=True,
    )
    start_date = fields.Date(string="Start Date (Начало)")
    end_date = fields.Date(string="End Date (Край)")
    days_in_insurance = fields.Integer(
        string="Days in Insurance (Дни в осигуряване)",
    )
    days_without_pay = fields.Integer(
        string="Days Without Pay (Дни без заплащане)",
    )

    # Income and contributions
    insurance_income = fields.Float(
        string="Insurance Income (Осиг. доход)",
        digits=(12, 2),
    )
    supplementary_insurance_income = fields.Float(
        string="Supplementary Income (Допълн. осиг. доход)",
        digits=(12, 2),
    )
    doo_employee = fields.Float(
        string="DOO — Employee (ДОО работник)",
        digits=(12, 2),
    )
    doo_employer = fields.Float(
        string="DOO — Employer (ДОО работодател)",
        digits=(12, 2),
    )
    health_employee = fields.Float(
        string="Health Ins. — Employee (ЗО работник)",
        digits=(12, 2),
    )
    health_employer = fields.Float(
        string="Health Ins. — Employer (ЗО работодател)",
        digits=(12, 2),
    )
    dzpo_employee = fields.Float(
        string="DZPO — Employee (ДЗПО работник)",
        digits=(12, 2),
    )
    dzpo_employer = fields.Float(
        string="DZPO — Employer (ДЗПО работодател)",
        digits=(12, 2),
    )
    tax_income = fields.Float(
        string="Tax Base (Данъчна основа)",
        digits=(12, 2),
    )
    tax_amount = fields.Float(
        string="Income Tax (Данък)",
        digits=(12, 2),
    )


class NraDeclarationD1(models.Model):
    _inherit = "nra.declaration"

    d1_line_ids = fields.One2many(
        "nra.declaration.d1.line",
        "declaration_id",
        string="Insured Persons (Осигурени лица)",
        states={"draft": [("readonly", False)]},
    )
    d1_line_count = fields.Integer(
        compute="_compute_d1_line_count",
        string="Line Count",
    )
    d1_correction_type = fields.Selection(
        selection=[
            ("0", "Редовна (Regular)"),
            ("1", "Коригираща (Correction)"),
            ("2", "Заличаваща (Deletion)"),
        ],
        string="Correction Type",
        default="0",
        states={"draft": [("readonly", False)]},
    )

    @api.depends("d1_line_ids")
    def _compute_d1_line_count(self):
        for rec in self:
            rec.d1_line_count = len(rec.d1_line_ids)

    def _get_file_record_count(self):
        self.ensure_one()
        if self.declaration_type != "d1":
            return super()._get_file_record_count()
        return len(self.d1_line_ids)

    def _prepare_xml_data(self):
        self.ensure_one()
        if self.declaration_type != "d1":
            return super()._prepare_xml_data()
        return {
            "eik": self.l10n_bg_uic,
            "month": self.period_month,
            "year": self.period_year,
            "correction_type": self.d1_correction_type,
            "lines": [
                {
                    "egn_lnch": line.egn_lnch,
                    "id_type": line.id_type,
                    "person_names": line.person_names,
                    "insurance_type": line.insurance_type,
                    "start_date": line.start_date and line.start_date.strftime("%Y-%m-%d"),
                    "end_date": line.end_date and line.end_date.strftime("%Y-%m-%d"),
                    "days_in_insurance": line.days_in_insurance,
                    "days_without_pay": line.days_without_pay,
                    "insurance_income": line.insurance_income,
                    "supplementary_insurance_income": line.supplementary_insurance_income,
                    "doo_employee": line.doo_employee,
                    "doo_employer": line.doo_employer,
                    "health_employee": line.health_employee,
                    "health_employer": line.health_employer,
                    "dzpo_employee": line.dzpo_employee,
                    "dzpo_employer": line.dzpo_employer,
                    "tax_income": line.tax_income,
                    "tax_amount": line.tax_amount,
                }
                for line in self.d1_line_ids
            ],
        }

    def _build_xml_tree(self, data):
        self.ensure_one()
        if self.declaration_type != "d1":
            return super()._build_xml_tree(data)

        root = etree.Element("Declaration", type="D1")
        header = etree.SubElement(root, "Header")
        etree.SubElement(header, "EIK").text = data["eik"]
        etree.SubElement(header, "Month").text = str(data["month"])
        etree.SubElement(header, "Year").text = str(data["year"])
        etree.SubElement(header, "CorrectionType").text = data["correction_type"]

        records = etree.SubElement(root, "Records")
        for line_data in data.get("lines", []):
            record = etree.SubElement(records, "Record")
            etree.SubElement(record, "IDType").text = line_data["id_type"]
            etree.SubElement(record, "EGNLNCH").text = line_data["egn_lnch"]
            etree.SubElement(record, "PersonNames").text = line_data["person_names"]
            etree.SubElement(record, "InsuranceType").text = line_data["insurance_type"]
            if line_data.get("start_date"):
                etree.SubElement(record, "StartDate").text = line_data["start_date"]
            if line_data.get("end_date"):
                etree.SubElement(record, "EndDate").text = line_data["end_date"]
            etree.SubElement(record, "DaysInInsurance").text = str(
                line_data["days_in_insurance"]
            )
            etree.SubElement(record, "DaysWithoutPay").text = str(
                line_data["days_without_pay"]
            )
            etree.SubElement(record, "InsuranceIncome").text = f"{line_data['insurance_income']:.2f}"
            etree.SubElement(record, "SupplementaryInsuranceIncome").text = (
                f"{line_data['supplementary_insurance_income']:.2f}"
            )
            etree.SubElement(record, "DOOEmployee").text = f"{line_data['doo_employee']:.2f}"
            etree.SubElement(record, "DOOEmployer").text = f"{line_data['doo_employer']:.2f}"
            etree.SubElement(record, "HealthEmployee").text = f"{line_data['health_employee']:.2f}"
            etree.SubElement(record, "HealthEmployer").text = f"{line_data['health_employer']:.2f}"
            etree.SubElement(record, "DZPOEmployee").text = f"{line_data['dzpo_employee']:.2f}"
            etree.SubElement(record, "DZPOEmployer").text = f"{line_data['dzpo_employer']:.2f}"
            etree.SubElement(record, "TaxIncome").text = f"{line_data['tax_income']:.2f}"
            etree.SubElement(record, "TaxAmount").text = f"{line_data['tax_amount']:.2f}"

        return root
