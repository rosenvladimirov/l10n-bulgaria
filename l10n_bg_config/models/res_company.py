#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models
from odoo.tools import sql

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
    l10n_bg_departament_code = fields.Integer("Departament code")
    l10n_bg_config_template = fields.Binary("Config Template")
    l10n_bg_key = fields.Char(related="partner_id.l10n_bg_key", readonly=False)

    def init(self):
        super().init()
        if not sql.column_exists(self.env.cr, self._table, "is_l10n_bg_record"):
            self.env.cr.execute("ALTER TABLE res_company ADD COLUMN is_l10n_bg_record boolean;")
        if not sql.column_exists(self.env.cr, self._table, "is_l10n_bg_multilanguage"):
            self.env.cr.execute("ALTER TABLE res_company ADD COLUMN is_l10n_bg_multilanguage boolean;")

    def _compute_l10n_bg_represent_contact_id(self):
        for record in self:
            represent_contact_id = record.partner_id.child_ids.filtered(
                lambda r: r.type == "represent"
            )
            if len(represent_contact_id) > 1:
                represent_contact_id = represent_contact_id[1]
            record.l10n_bg_represent_contact_id = represent_contact_id

    def _inverse_l10n_bg_represent_contact_id(self):
        for record in self:
            if record.l10n_bg_represent_contact_id:
                record.l10n_bg_represent_contact_id.type = "represent"
                record.partner_id.child_ids = [
                    Command.link(record.l10n_bg_represent_contact_id.id)
                ]

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
