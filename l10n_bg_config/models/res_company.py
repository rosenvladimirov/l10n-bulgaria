#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
import logging
import re

from odoo import Command, api, fields, models
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)

L10N_BG_MULTILANGUAGE = ("l10n_bg_multilang", "partner_multilang")

# КИД-2008 / NACE Rev.2 division → section ranges (виж одобрения spec за
# init free-text КИД). Резолва числов КИД код до секция дори когато само
# 21-те секции са seed-нати (без l10n_bg_payroll_classifications няма
# division/group/class йерархия). Текущият КИД-2025 seed запазва
# 21-буквената схема A..U, затова една таблица обслужва и двете издания;
# 2025 J→K разделянето ще се добави per-edition щом официалните 2025
# раздели се финализират.
_L10N_BG_KID_DIVISION_SECTION = (
    (1, 3, "A"), (5, 9, "B"), (10, 33, "C"), (35, 35, "D"),
    (36, 39, "E"), (41, 43, "F"), (45, 47, "G"), (49, 53, "H"),
    (55, 56, "I"), (58, 63, "J"), (64, 66, "K"), (68, 68, "L"),
    (69, 75, "M"), (77, 82, "N"), (84, 84, "O"), (85, 85, "P"),
    (86, 88, "Q"), (90, 93, "R"), (94, 96, "S"), (97, 98, "T"),
    (99, 99, "U"),
)


class ResCompany(models.Model):
    _inherit = "res.company"

    is_l10n_bg_record = fields.Boolean(
        string="Bulgaria - Use Bulgaria Accounting",
        compute="_compute_is_l10n_bg_record",
        inverse="_inverse_is_l10n_bg_record",
        default=True,
        store=True,
    )
    is_l10n_bg_multilanguage = fields.Json(
        string="Bulgaria - Multilanguage",
        compute="_compute_is_l10n_bg_multilanguage",
        inverse="_inverse_is_l10n_bg_multilanguage",
        help="Allows to set multilanguage in Bulgaria accounting",
        store=True,
    )
    is_l10n_bg_tax_report = fields.Boolean(
        string="Bulgaria - Tax Report",
        help="Allows to set tax report in Bulgaria accounting",
    )
    is_l10n_bg_tax_report_with_vat = fields.Boolean(
        string="Bulgaria - Tax Report with VAT",
    )
    l10n_bg_uic_type = fields.Selection(
        related="partner_id.l10n_bg_uic_type",
        readonly=True,
    )
    l10n_bg_uic = fields.Char(
        related="partner_id.l10n_bg_uic",
        readonly=True,
    )
    # Праг „незначителна стойност" (ЗДДС, §1 от ДР) — разделя мостра/рекламен
    # материал (под прага, не е доставка по чл. 6, ал. 4) от дарение (над
    # прага — приравнена доставка със самоначисляване). Единична пазарна
    # стойност на артикул. 0 = не е конфигуриран → всичко безвъзмездно се
    # третира консервативно като дарение.
    l10n_bg_insignificant_value_threshold = fields.Monetary(
        string="Insignificant Value Threshold",
        currency_field="currency_id",
        default=0.0,
        help="Unit market value threshold below which a free-of-charge good "
             "counts as an advertising item / sample (not a supply under the "
             "VAT Act) instead of a donation. Set per the current legal "
             "definition of 'goods of insignificant value' (VAT Act, "
             "Additional Provisions). 0 disables the split — every "
             "free-of-charge supply is treated as a donation.",
    )
    l10n_bg_represent_contact_id = fields.Many2one(
        "res.partner",
        string="Representative",
        compute="_compute_l10n_bg_represent_contact_id",
        inverse="_inverse_l10n_bg_represent_contact_id",
        store=True,
    )
    l10n_bg_kid_version = fields.Selection(
        selection=[("2008", "KID-2008"), ("2025", "KID-2025")],
        string="KID edition",
        default="2025",
        help="KID edition used when deriving the primary economic activity.",
    )
    l10n_bg_primary_kid_id = fields.Many2one(
        "l10n.bg.kid",
        string="Primary economic activity (KID)",
        domain="[('level', '=', 'section'), "
        "('kid_version', '=', l10n_bg_kid_version)]",
        help="Main activity derived from the net sales revenue accounts "
        "following the НСИ methodology (highest relative share of net "
        "sales revenue). Recompute via the КИД derivation wizard.",
    )
    l10n_bg_kid_ids = fields.Many2many(
        "l10n.bg.kid",
        relation="res_company_l10n_bg_kid_rel",
        column1="company_id",
        column2="kid_id",
        string="Active KID sectors",
        domain="[('level', '=', 'section'), "
        "('kid_version', '=', l10n_bg_kid_version)]",
        help="KID sectors this company operates in. Drives the "
        "chart-of-accounts install filter: at base install this is "
        "empty, so only universal accounts load; selecting a sector "
        "(and reloading the chart template) lets its sector-specific "
        "accounts through.",
    )
    l10n_bg_kid_codes = fields.Char(
        string="KID codes (init)",
        help="Free-text list of KID activity codes captured at company "
        "setup (e.g. '41, 43.21, F' or '6201'). Parsed into 'Active "
        "KID sectors' when the chart of accounts is loaded and that "
        "field is still empty (text = bootstrap, the sector list is "
        "authoritative once set). Use 'Resolve from codes' to "
        "re-parse on demand.",
    )
    l10n_bg_departament_code = fields.Integer("Departament code")
    l10n_bg_config_template = fields.Binary("Config Template", attachment=False)
    l10n_bg_key = fields.Char(related="partner_id.l10n_bg_key", readonly=False)

    def _compute_l10n_bg_represent_contact_id(self):
        for record in self:
            represent_contact_id = record.partner_id.child_ids.filtered(
                lambda r: r.type == "represent"
            )
            if len(represent_contact_id) > 1:
                represent_contact_id = represent_contact_id[0]
            record.l10n_bg_represent_contact_id = represent_contact_id

    def _inverse_l10n_bg_represent_contact_id(self):
        for record in self:
            if record.l10n_bg_represent_contact_id:
                record.l10n_bg_represent_contact_id.type = "represent"
                record.partner_id.child_ids = [
                    Command.link(record.l10n_bg_represent_contact_id.id)
                ]
            else:
                record.l10n_bg_represent_contact_id = False
                record.partner_id.child_ids.filtered(lambda r: r.id == record.id).type = "contact"

    @api.depends("chart_template")
    def _compute_is_l10n_bg_record(self):
        for record in self:
            record.is_l10n_bg_record = record._check_is_l10n_bg_record(company=record.parent_id)

    def _inverse_is_l10n_bg_record(self):
        for company in self:
            if company.is_l10n_bg_record and company.chart_template == "bg":
                company.is_l10n_bg_record = True
            elif company.chart_template != "bg":
                l10n_bg = self.env["ir.module.module"].search(
                    [("name", "=", "l10n_bg"), ("state", "!=", "installed")]
                )
                if l10n_bg:
                    l10n_bg.button_immediate_install()
            else:
                company.is_l10n_bg_record = False

    def _inverse_is_l10n_bg_multilanguage(self):
        for company in self:
            l10n_bg = self.env["ir.module.module"].search(
                [
                    ("name", "in", L10N_BG_MULTILANGUAGE),
                    ("state", "=", "installed"),
                ]
            )
            company.is_l10n_bg_multilanguage = dict([(x.name, x.state) for x in l10n_bg])

    def _compute_is_l10n_bg_multilanguage(self):
        for record in self:
            record.is_l10n_bg_multilanguage = record.is_l10n_bg_multilanguage if record.is_l10n_bg_multilanguage else {}

    def _check_is_l10n_bg_record(self, company=False):
        if company and isinstance(company, int):
            company = self.browse(company)
        elif not company:
            company = self
        return company.chart_template == "bg"

    @staticmethod
    def _xml_to_dict(xml_text):
        root = ET.fromstring(xml_text)
        res = {}
        for setting in root.findall('.//settings/setting'):
            model = setting.get('model')
            field = setting.get('field')
            value_type = setting.get('value')
            codes = setting.text.strip().split(',')

            if model not in res:
                res[model] = {}
            if field not in res[model]:
                res[model][field] = {}

            res[model][field][value_type] = codes
        return res

    def xml_to_dict(self, xml_text):
        old_settings = self.l10n_bg_config_template and json.loads(self.l10n_bg_config_template) or {}
        res = self._xml_to_dict(xml_text)
        if res:
            old_settings.update(res)
            new_settings = json.dumps(old_settings).encode('utf-8')
            self.write({
                'l10n_bg_config_template': new_settings
                })
        return self.l10n_bg_config_template and json.loads(self.l10n_bg_config_template) or {}

    def _process_config_file(self):
        pass

    def action_process_config_file(self):
        self._process_config_file()

    def _l10n_bg_compute_primary_kid(self, date_from=False, date_to=False):
        """Rank КИД sections by net sales revenue (НСИ methodology).

        The main economic activity is the one with the highest relative
        share of net sales revenue. We sum ``credit - debit`` of posted
        journal items on the accounts mapped (``revenue_indicator=True``)
        to each КИД, in the optional ``[date_from, date_to]`` window, and
        roll the result up to the section level.

        Limitation: a revenue code shared by several sections (e.g. 703 →
        services) contributes to each of them, so 701 (production) / 702
        (trade) / 704 (rent) are the decisive signals; finer per-section
        attribution would require analytic accounts.

        :return: ordered list of ``(section_kid, net_revenue)`` desc; also
                 writes ``l10n_bg_primary_kid_id`` on each company.
        """
        self.ensure_one()
        Map = self.env["l10n.bg.account.industry.map"]
        AML = self.env["account.move.line"]

        rows = Map.search(
            [
                ("revenue_indicator", "=", True),
                ("kid_version", "=", self.l10n_bg_kid_version),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.id),
            ]
        )

        revenue_by_section = {}
        for row in rows:
            section = row.kid_id
            while section.parent_id:
                section = section.parent_id
            accounts = row._resolve_accounts(self)
            if not accounts:
                continue
            aml_domain = [
                ("account_id", "in", accounts.ids),
                ("parent_state", "=", "posted"),
                ("company_id", "=", self.id),
            ]
            if date_from:
                aml_domain.append(("date", ">=", date_from))
            if date_to:
                aml_domain.append(("date", "<=", date_to))
            groups = AML._read_group(
                aml_domain, [], ["debit:sum", "credit:sum"]
            )
            debit, credit = (groups[0] if groups else (0.0, 0.0))
            net_revenue = (credit or 0.0) - (debit or 0.0)
            if section:
                revenue_by_section.setdefault(section, 0.0)
                revenue_by_section[section] += net_revenue

        ranking = sorted(
            revenue_by_section.items(), key=lambda kv: kv[1], reverse=True
        )
        if ranking and ranking[0][1] > 0:
            self.l10n_bg_primary_kid_id = ranking[0][0].id
        return ranking

    def action_l10n_bg_compute_primary_kid(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Derive primary economic activity (КИД)",
            "res_model": "l10n.bg.kid.compute.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_company_id": self.id},
        }

    def _l10n_bg_resolve_one_kid_code(self, token, kid_version):
        """Резолва един КИД токен до неговата секция (или празно).

        Разпознава нивото по формата: 1 буква = секция; иначе се
        нормализира до числа (``6103`` → ``61.03``). Първо опитва точно
        съвпадение по код (пълна йерархия, когато
        ``l10n_bg_payroll_classifications`` я seed-ва) и се изкачва до
        секцията; ако няма йерархия — fallback през статичната
        раздел→секция таблица. Връща празен recordset при неразпознат
        код (никога не вдига грешка).
        """
        Kid = self.env["l10n.bg.kid"]
        text = (token or "").strip().upper()
        if not text:
            return Kid
        # Самостоятелна буква на секция (A..U / A..V за 2025).
        if len(text) == 1 and text.isalpha():
            return Kid.search(
                [
                    ("code", "=", text),
                    ("kid_version", "=", kid_version),
                    ("level", "=", "section"),
                ],
                limit=1,
            )
        digits = re.sub(r"\D", "", text)
        if not digits:
            return Kid
        # Нормализация към Odoo КИД пунктуация: XXXX → XX.XX, XXX → XX.X.
        if len(digits) == 3:
            norm = f"{digits[:2]}.{digits[2:]}"
        elif len(digits) >= 4:
            norm = f"{digits[:2]}.{digits[2:4]}"
        else:
            norm = digits[:2]
        rec = Kid.search(
            [
                ("code", "in", list({norm, digits})),
                ("kid_version", "=", kid_version),
            ],
            limit=1,
        )
        if rec:
            while rec.parent_id:
                rec = rec.parent_id
            return rec
        # Fallback: статична раздел→секция таблица (само-секции install).
        division = int(digits[:2])
        for low, high, letter in _L10N_BG_KID_DIVISION_SECTION:
            if low <= division <= high:
                return Kid.search(
                    [
                        ("code", "=", letter),
                        ("kid_version", "=", kid_version),
                        ("level", "=", "section"),
                    ],
                    limit=1,
                )
        return Kid

    def _l10n_bg_resolve_kid_codes(self, text, kid_version):
        """Парсва свободен списък КИД кодове до ``l10n.bg.kid`` секции.

        Токенизира по ``, ; whitespace newline``, резолва всеки токен
        през :meth:`_l10n_bg_resolve_one_kid_code` и връща уникалните
        секции. Неразпознат токен се логва и се прескача — никога не
        проваля import-а (default-keep философия).

        :return: ``l10n.bg.kid`` recordset от различни секции.
        """
        Kid = self.env["l10n.bg.kid"]
        if not text:
            return Kid
        sections = Kid
        for raw in re.split(r"[,;\s]+", text.strip()):
            token = raw.strip()
            if not token:
                continue
            section = self._l10n_bg_resolve_one_kid_code(token, kid_version)
            if section:
                sections |= section
            else:
                _logger.warning(
                    "l10n_bg KID init: unrecognised code %r (edition %s) "
                    "— skipped",
                    token,
                    kid_version,
                )
        return sections

    def action_l10n_bg_resolve_kid_codes(self):
        """Ръчно пре-парсва ``l10n_bg_kid_codes`` → ``l10n_bg_kid_ids``.

        За разлика от auto-bootstrap-а при chart load, бутонът ВИНАГИ
        презаписва секторния M2M от текста (изричен потребителски акт).
        """
        for company in self:
            sections = company._l10n_bg_resolve_kid_codes(
                company.l10n_bg_kid_codes, company.l10n_bg_kid_version
            )
            company.l10n_bg_kid_ids = [Command.set(sections.ids)]
        return True
