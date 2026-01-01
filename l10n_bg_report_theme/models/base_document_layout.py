#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models
from odoo.addons.l10n_bg_report_theme.wizards.base_document_layout_colors import get_odoo_home_scss_dir, \
    get_scss_file_path, copy_scss_to_home
from odoo import tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Константи за референции към отчети
REPORT_REFS = {
    'layout': 'l10n_bg_report_theme.report_layout_sections',
    'address_layout': 'l10n_bg_report_theme.address_layout',
    'invoice': 'l10n_bg_report_theme.report_invoice_document',
    'purchase_quotation': 'l10n_bg_report_theme.report_purchasequotation_document',
    'purchase_order': 'l10n_bg_report_theme.report_purchaseorder_document',
    'sale_order': 'l10n_bg_report_theme.report_saleorder_document',
    'sale_order_raw': 'l10n_bg_report_theme.report_saleorder_raw',
    'sale_order_pro_forma': 'l10n_bg_report_theme.report_saleorder_pro_forma',
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
    selection_colors = fields.One2many(
        'base.document.layout.colors',
        'base_document_layout_id',
        string='Colors',
    )

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        color_manager = self.env['base.document.layout.colors']
        colorset = color_manager.load_scss_colors()
        if colorset:
            res['selection_colors'] = colorset
            # Инициализиране на пътя в компанията
            company = self.env.company
            if company:
                from odoo.addons.l10n_bg_report_theme.wizards.base_document_layout_colors import get_scss_file_path
                new_path = get_scss_file_path(use_custom=True, company_id=company.id)
                if company.custom_scss_path != new_path:
                    company.custom_scss_path = new_path
                self.env.registry.clear_cache('assets')
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
                report.with_context(**dict(self.env.context, active_test=False)).active = \
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

    def action_reset_to_default(self):
        """Копира отново оригиналния SCSS файл от модула в home директорията"""
        try:
            company = self.company_id or self.env.company
            # Вземи пътищата
            source_path = get_scss_file_path(use_custom=False)  # От модула
            target_path = get_scss_file_path(use_custom=True, company_id=company.id)  # В home

            # Копирай файла (презаписва съществуващия)
            copy_scss_to_home(company_id=company.id)
            _logger.info(f"Reset SCSS: copied {source_path} to {target_path}")

            # Презареди цветовете от файла
            color_manager = self.env['base.document.layout.colors']
            self.selection_colors = color_manager.load_scss_colors(company_id=company.id)

            # Актуализирай динамичния асет на Odoo 19.0
            if hasattr(company, '_update_asset_style'):
                company._update_asset_style()

            # Инвалидиране на асетите
            self.env.registry.clear_cache('assets')

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'SCSS the file is restored to the original and the colors are reloaded',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            error_msg = f"Recovery error: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)

    def get_custom_scss_content(self):
        return self.company_id.get_custom_scss_content()

    def get_layout_scss_content(self):
        return self.company_id.get_layout_scss_content()
