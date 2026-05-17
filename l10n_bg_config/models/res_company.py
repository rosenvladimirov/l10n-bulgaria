#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json

from odoo import Command, api, fields, models
import xml.etree.ElementTree as ET

L10N_BG_MULTILANGUAGE = ("l10n_bg_multilang", "partner_multilang")


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
    l10n_bg_represent_contact_id = fields.Many2one(
        "res.partner",
        string="Representative",
        compute="_compute_l10n_bg_represent_contact_id",
        inverse="_inverse_l10n_bg_represent_contact_id",
        store=True,
    )
    l10n_bg_kid_version = fields.Selection(
        selection=[("2008", "КИД-2008"), ("2025", "КИД-2025")],
        string="КИД edition",
        default="2025",
        help="КИД edition used when deriving the primary economic activity.",
    )
    l10n_bg_primary_kid_id = fields.Many2one(
        "l10n.bg.kid",
        string="Primary economic activity (КИД)",
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
        string="Active КИД sectors",
        domain="[('level', '=', 'section'), "
        "('kid_version', '=', l10n_bg_kid_version)]",
        help="КИД sectors this company operates in. Drives the "
        "chart-of-accounts install filter: at base install this is "
        "empty, so only universal accounts load; selecting a sector "
        "(and reloading the chart template) lets its sector-specific "
        "accounts through.",
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
