# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = "base.document.layout"

    layout_background_header_image = fields.Binary(
        related="company_id.layout_background_header_image", readonly=False
    )
    layout_background_footer_image = fields.Binary(
        related="company_id.layout_background_footer_image", readonly=False
    )
    logo_print = fields.Binary(related="company_id.logo_print", readonly=False)
    preview_logo_print = fields.Binary(
        related="logo_print", string="Preview print logo"
    )
    logo_print_primary_color = fields.Char(compute="_compute_logo_print_colors")
    logo_print_secondary_color = fields.Char(compute="_compute_logo_print_colors")

    # Those following fields are required as a company to create invoice report
    mobile = fields.Char(related="company_id.mobile", readonly=True)
    # sender = fields.Many2one(related='company_id.partner_id', readonly=True)
    # recipient = fields.Many2one(related='company_id.partner_id', readonly=True)

    @api.onchange("logo_print")
    def _onchange_logo_print(self):
        for wizard in self:
            # It is admitted that if the user puts the original image back, it won't change colors
            company = wizard.company_id
            # at that point wizard.logo has been assigned the value present in DB
            if (
                wizard.logo_print == company.logo_print
                and company.primary_color
                and company.secondary_color
            ):
                continue

            if wizard.logo_primary_color:
                wizard.primary_color = wizard.logo_primary_color
            if wizard.logo_secondary_color:
                wizard.secondary_color = wizard.logo_secondary_color

    @api.depends("logo_print")
    def _compute_logo_print_colors(self):
        for wizard in self:
            if wizard._context.get("bin_size"):
                wizard_for_image = wizard.with_context(bin_size=False)
            else:
                wizard_for_image = wizard
            (
                wizard.logo_print_primary_color,
                wizard.logo_print_secondary_color,
            ) = wizard.extract_image_primary_secondary_colors(
                wizard_for_image.logo_print
            )
            wizard.logo_primary_color, wizard.logo_secondary_color = (
                wizard.logo_print_primary_color,
                wizard.logo_print_secondary_color,
            )
