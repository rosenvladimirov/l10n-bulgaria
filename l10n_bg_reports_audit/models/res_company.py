#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json

from odoo import Command, _, api, fields, models

L10N_BG_INTRASTAT = [
    ("standard", "Standard base on levelling up"),
    ("statistical", "Statistical base on levelling up"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_bg_intra_stat_type = fields.Selection(
        L10N_BG_INTRASTAT, string="Level of registration"
    )
    l10n_bg_intra_stat_incomes = fields.Boolean(
        "An obligation to submit intra-Community supplies"
    )
    l10n_bg_intra_stat_outcomes = fields.Boolean(
        "An obligation to submit intra-Community incomes"
    )
    l10n_bg_odoo_compatible = fields.Boolean("Odoo compatible")
    l10n_bg_tax_contact_id = fields.Many2one(
        "res.partner",
        string="TAX Report creator",
        compute="_compute_l10n_bg_tax_contact_id",
        inverse="_inverse_l10n_bg_tax_contact_id",
        store=True,
    )

    @api.depends("partner_id")
    def _compute_l10n_bg_tax_contact_id(self):
        for record in self:
            l10n_bg_tax_contact_id = record.partner_id.child_ids.filtered(
                lambda r: r.type == "represent"
            )
            if len(l10n_bg_tax_contact_id) > 1:
                l10n_bg_tax_contact_id = l10n_bg_tax_contact_id[0]
            record.l10n_bg_tax_contact_id = l10n_bg_tax_contact_id

    @api.depends("partner_id")
    def _inverse_l10n_bg_tax_contact_id(self):
        for record in self:
            if record.l10n_bg_tax_contact_id:
                if record.l10n_bg_tax_contact_id.type not in ["represent", "agent", "tax"]:
                    record.l10n_bg_tax_contact_id.type = "represent"
                record.partner_id.child_ids = [
                    Command.link(record.l10n_bg_tax_contact_id.id)
                ]
            else:
                record.l10n_bg_tax_contact_id = False
                record.partner_id.child_ids.filtered(lambda r: r.id == record.id).type = "contact"

    def _process_l10n_bg_report_audit_config_file(self):
        file_content_json = self.l10n_bg_config_template and json.loads(self.l10n_bg_config_template) or {}
        for key, value in file_content_json.get('account.account.tag', {}).items():
            for tag_key, tags in value.items():
                tag_id = self.env['account.account.tag'].search([('name', 'in', list(map(str, tags)))])
                if tag_id:
                    tag_id.write({
                        key: tag_key
                    })
