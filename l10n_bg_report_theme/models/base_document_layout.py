# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools
from odoo.tools import format_date, format_datetime, format_time


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

    def _get_render_information(self, styles):
        res = super()._get_render_information(styles)
        env = self.env
        res.update(
            {
                "format_date": lambda date,
                                      lang_code=False,
                                      date_format=False: format_date(
                    env, date, lang_code=lang_code, date_format=date_format
                ),
                "format_datetime": lambda dt,
                                          tz=False,
                                          dt_format=False,
                                          lang_code=False: format_datetime(
                    env, dt, tz=tz, dt_format=dt_format, lang_code=lang_code
                ),
                "format_time": lambda time,
                                      tz=False,
                                      time_format=False,
                                      lang_code=False: format_time(
                    env, time, tz=tz, time_format=time_format, lang_code=lang_code
                ),
                "format_amount": lambda amount,
                                        currency,
                                        lang_code=False: tools.format_amount(env, amount, currency, lang_code),
                "format_duration": lambda value: tools.format_duration(value),
            }
        )
        return res
