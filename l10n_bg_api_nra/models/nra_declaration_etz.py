import logging

from lxml import etree

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

ETZ_CONTRACT_TYPES = [
    ("01", "01 — Безсрочен трудов договор"),
    ("02", "02 — Срочен трудов договор"),
    ("03", "03 — Трудов договор за стажуване"),
    ("04", "04 — Трудов договор за обучение"),
    ("05", "05 — Трудов договор за надомна работа"),
    ("06", "06 — Трудов договор за работа от разстояние"),
    ("07", "07 — Трудов договор за краткотрайна сезонна работа"),
    ("10", "10 — Допълнителен трудов договор при същия работодател"),
    ("11", "11 — Допълнителен трудов договор при друг работодател"),
]

ETZ_RECORD_TYPES = [
    ("new", "Регистриране (New)"),
    ("correction", "Коригиране (Correction)"),
    ("deletion", "Заличаване (Deletion)"),
]

ETZ_TERMINATION_GROUNDS = [
    ("325_1_1", "Чл. 325, ал. 1, т. 1 — По взаимно съгласие"),
    ("325_1_2", "Чл. 325, ал. 1, т. 2 — Изтичане на срока"),
    ("325_1_3", "Чл. 325, ал. 1, т. 3 — Завършване на работата"),
    ("326", "Чл. 326 — С предизвестие от работника"),
    ("328_1_1", "Чл. 328, ал. 1, т. 1 — Закриване на предприятието"),
    ("328_1_2", "Чл. 328, ал. 1, т. 2 — Съкращаване на щата"),
    ("328_1_3", "Чл. 328, ал. 1, т. 3 — Намаляване обема на работата"),
    ("330_1_1", "Чл. 330, ал. 1, т. 1 — Задържане повече от 2 месеца"),
    ("331", "Чл. 331 — Срещу обезщетение"),
]


class NraDeclarationEtzLine(models.Model):
    _name = "nra.declaration.etz.line"
    _description = "Electronic Labor Record Line"
    _order = "sequence, id"

    declaration_id = fields.Many2one(
        "nra.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)

    # Record type
    record_type = fields.Selection(
        selection=ETZ_RECORD_TYPES,
        string="Record Type (Тип запис)",
        required=True,
        default="new",
    )

    # Employee identification
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

    # Contract data
    contract_type = fields.Selection(
        selection=ETZ_CONTRACT_TYPES,
        string="Contract Type (Вид договор)",
        required=True,
    )
    contract_number = fields.Char(
        string="Contract Number (Номер на договор)",
    )
    contract_date = fields.Date(
        string="Contract Date (Дата на договор)",
        required=True,
    )
    start_date = fields.Date(
        string="Start Date (Начална дата)",
        required=True,
    )
    end_date = fields.Date(
        string="End Date (Крайна дата)",
    )

    # Position and workplace
    position_code = fields.Char(
        string="Position Code (НКПД)",
        size=8,
    )
    position_name = fields.Char(
        string="Position (Длъжност)",
    )
    workplace_code = fields.Char(
        string="Workplace Code (Код на раб. място)",
    )

    # Termination
    termination_date = fields.Date(
        string="Termination Date (Дата на прекратяване)",
    )
    termination_ground = fields.Selection(
        selection=ETZ_TERMINATION_GROUNDS,
        string="Termination Ground (Основание)",
    )

    # Working time
    working_hours = fields.Float(
        string="Working Hours (Раб. време в часове)",
    )
    working_days_per_week = fields.Integer(
        string="Working Days/Week (Раб. дни/седмица)",
        default=5,
    )


class NraDeclarationEtz(models.Model):
    _inherit = "nra.declaration"

    etz_line_ids = fields.One2many(
        "nra.declaration.etz.line",
        "declaration_id",
        string="Labor Records (Трудови записи)",
        states={"draft": [("readonly", False)]},
    )
    etz_line_count = fields.Integer(
        compute="_compute_etz_line_count",
        string="Line Count",
    )

    @api.depends("etz_line_ids")
    def _compute_etz_line_count(self):
        for rec in self:
            rec.etz_line_count = len(rec.etz_line_ids)

    def _prepare_xml_data(self):
        self.ensure_one()
        if self.declaration_type != "etz":
            return super()._prepare_xml_data()
        return {
            "eik": self.l10n_bg_uic,
            "month": self.period_month,
            "year": self.period_year,
            "lines": [
                {
                    "record_type": line.record_type,
                    "egn_lnch": line.egn_lnch,
                    "id_type": line.id_type,
                    "person_names": line.person_names,
                    "contract_type": line.contract_type,
                    "contract_number": line.contract_number,
                    "contract_date": line.contract_date
                    and line.contract_date.strftime("%Y-%m-%d"),
                    "start_date": line.start_date
                    and line.start_date.strftime("%Y-%m-%d"),
                    "end_date": line.end_date
                    and line.end_date.strftime("%Y-%m-%d"),
                    "position_code": line.position_code,
                    "position_name": line.position_name,
                    "workplace_code": line.workplace_code,
                    "termination_date": line.termination_date
                    and line.termination_date.strftime("%Y-%m-%d"),
                    "termination_ground": line.termination_ground,
                    "working_hours": line.working_hours,
                    "working_days_per_week": line.working_days_per_week,
                }
                for line in self.etz_line_ids
            ],
        }

    def _build_xml_tree(self, data):
        self.ensure_one()
        if self.declaration_type != "etz":
            return super()._build_xml_tree(data)

        root = etree.Element("ElectronicLaborRecords")
        header = etree.SubElement(root, "Header")
        etree.SubElement(header, "EIK").text = data["eik"]
        if data.get("month"):
            etree.SubElement(header, "Month").text = str(data["month"])
        if data.get("year"):
            etree.SubElement(header, "Year").text = str(data["year"])

        records = etree.SubElement(root, "Records")
        for line_data in data.get("lines", []):
            record = etree.SubElement(records, "Record")
            etree.SubElement(record, "RecordType").text = line_data["record_type"]
            etree.SubElement(record, "IDType").text = line_data["id_type"]
            etree.SubElement(record, "EGNLNCH").text = line_data["egn_lnch"]
            etree.SubElement(record, "PersonNames").text = line_data["person_names"]
            etree.SubElement(record, "ContractType").text = line_data["contract_type"]
            if line_data.get("contract_number"):
                etree.SubElement(record, "ContractNumber").text = line_data[
                    "contract_number"
                ]
            etree.SubElement(record, "ContractDate").text = line_data["contract_date"]
            etree.SubElement(record, "StartDate").text = line_data["start_date"]
            if line_data.get("end_date"):
                etree.SubElement(record, "EndDate").text = line_data["end_date"]
            if line_data.get("position_code"):
                etree.SubElement(record, "PositionCode").text = line_data[
                    "position_code"
                ]
            if line_data.get("position_name"):
                etree.SubElement(record, "PositionName").text = line_data[
                    "position_name"
                ]
            if line_data.get("workplace_code"):
                etree.SubElement(record, "WorkplaceCode").text = line_data[
                    "workplace_code"
                ]
            if line_data.get("termination_date"):
                etree.SubElement(record, "TerminationDate").text = line_data[
                    "termination_date"
                ]
            if line_data.get("termination_ground"):
                etree.SubElement(record, "TerminationGround").text = line_data[
                    "termination_ground"
                ]
            if line_data.get("working_hours"):
                etree.SubElement(record, "WorkingHours").text = str(
                    line_data["working_hours"]
                )
            if line_data.get("working_days_per_week"):
                etree.SubElement(record, "WorkingDaysPerWeek").text = str(
                    line_data["working_days_per_week"]
                )

        return root
