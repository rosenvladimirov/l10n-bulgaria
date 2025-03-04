#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, api, fields, models

L10N_BG_INTRASTAT = [
    ("standard", _("Standard base on levelling up")),
    ("statistical", _("Statistical base on levelling up")),
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
        compute="_compute_l10n_bg_represent_contact_id",
        inverse="_inverse_l10n_bg_represent_contact_id",
        store=True,
    )

    @api.depends("partner_id")
    def _compute_l10n_bg_represent_contact_id(self):
        for record in self:
            tax_contact_id = record.partner_id.child_ids.filtered(
                lambda r: r.type == "represent"
            )
            if len(tax_contact_id) > 1:
                tax_contact_id = tax_contact_id[1]
            record.l10n_bg_tax_contact_id = tax_contact_id

    @api.depends("partner_id")
    def _inverse_l10n_bg_represent_contact_id(self):
        for record in self:
            if record.l10n_bg_tax_contact_id:
                record.l10n_bg_tax_contact_id.type = "represent"
                record.partner_id.child_ids = [
                    Command.link(record.l10n_bg_tax_contact_id.id)
                ]
