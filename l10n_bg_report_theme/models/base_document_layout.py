# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from odoo import api, fields, models
from odoo import tools

_logger = logging.getLogger(__name__)

# Константи за референции към отчети
REPORT_REFS = {
    'layout': 'l10n_bg_report_theme.report_layout_sections',
    'invoice': 'l10n_bg_report_theme.report_invoice_document',
    'purchase_quotation': 'l10n_bg_report_theme.report_purchasequotation_document',
    'purchase_order': 'l10n_bg_report_theme.report_purchaseorder_document',
    'sale_order': 'l10n_bg_report_theme.report_saleorder_document',
}


class BaseDocumentLayout(models.TransientModel):
    _inherit = "base.document.layout"

    # Групиране на полета по тип изглед
    # Portrait изглед
    layout_background_header_image = fields.Binary(
        related="company_id.layout_background_header_image",
        readonly=False
    )
    layout_background_footer_image = fields.Binary(
        related="company_id.layout_background_footer_image",
        readonly=False
    )

    # Landscape изглед
    layout_background_l_image = fields.Binary(
        related="company_id.layout_background_l_image",
        readonly=False
    )
    layout_background_l_header_image = fields.Binary(
        related="company_id.layout_background_l_header_image",
        readonly=False
    )
    layout_background_l_footer_image = fields.Binary(
        related="company_id.layout_background_l_footer_image",
        readonly=False
    )

    # Лого и цветове
    logo_print = fields.Binary(
        related="company_id.logo_print",
        readonly=False
    )
    preview_logo_print = fields.Binary(
        related="logo_print",
        string="Preview print logo"
    )
    logo_print_primary_color = fields.Char(
        compute="_compute_logo_print_colors"
    )
    logo_print_secondary_color = fields.Char(
        compute="_compute_logo_print_colors"
    )

    # Информация за компанията
    mobile = fields.Char(
        related="company_id.mobile",
        readonly=True
    )
    selection_colors = fields.One2many(
        'base.document.layout.colors',
        'base_document_layout_id',
        string='Colors',
    )

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        colorset = self.env['base.document.layout.colors'].load_scss_colors()
        if colorset:
            res['selection_colors'] = colorset
        return res

    @api.onchange("logo_print")
    def _onchange_logo_print(self):
        for wizard in self:
            if self._should_skip_color_update(wizard):
                continue
            self._update_colors_from_logo(wizard)

    @staticmethod
    def _should_skip_color_update(wizard):
        company = wizard.company_id
        return (wizard.logo_print == company.logo_print and
                company.primary_color and
                company.secondary_color)

    def _update_colors_from_logo(self, wizard):
        if wizard.logo_primary_color:
            wizard.primary_color = wizard.logo_primary_color
        if wizard.logo_secondary_color:
            wizard.secondary_color = wizard.logo_secondary_color

    @api.depends("logo_print")
    def _compute_logo_print_colors(self):
        for wizard in self:
            wizard_for_image = wizard.with_context(bin_size=False) if wizard._context.get("bin_size") else wizard
            primary, secondary = wizard.extract_image_primary_secondary_colors(wizard_for_image.logo_print)
            wizard.logo_print_primary_color = primary
            wizard.logo_print_secondary_color = secondary
            wizard.logo_primary_color = primary
            wizard.logo_secondary_color = secondary

    def _get_render_information(self, styles):
        res = super()._get_render_information(styles)
        res.update(self._get_formatting_functions())
        return res

    def _get_formatting_functions(self):
        env = self.env
        return {
            "format_date": lambda date, lang_code=False, date_format=False:
            tools.format_date(env, date, lang_code=lang_code, date_format=date_format),
            "format_datetime": lambda dt, tz=False, dt_format=False, lang_code=False:
            tools.format_datetime(env, dt, tz=tz, dt_format=dt_format, lang_code=lang_code),
            "format_time": lambda time, tz=False, time_format=False, lang_code=False:
            tools.format_time(env, time, tz=tz, time_format=time_format, lang_code=lang_code),
            "format_amount": lambda amount, currency, lang_code=False:
            tools.format_amount(env, amount, currency, lang_code),
            "format_duration": lambda value: tools.format_duration(value),
        }

    def _update_active_report_layout(self):
        reports = {key: self.env.ref(ref, raise_if_not_found=False)
                   for key, ref in REPORT_REFS.items()}

        layout_id = reports['layout']
        for key, report in reports.items():
            if report and key != 'layout':
                report.with_context(**dict(self._context, active_test=False)).active = \
                    self.report_layout_id.id == layout_id.id

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        for template, values in zip(templates, vals_list):
            if values.get('external_report_layout_id'):
                template._update_active_report_layout()
        return templates

    def write(self, vals):
        res = super().write(vals)
        if vals.get('external_report_layout_id'):
            for template in self:
                template._update_active_report_layout()
        return res
