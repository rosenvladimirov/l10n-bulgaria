#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
from markupsafe import Markup

from odoo import fields, models
from odoo.modules.module import get_module_path
from odoo.addons.l10n_bg_report_theme.wizards.base_document_layout_colors import get_scss_file_path

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = "res.company"

    layout_background = fields.Selection(
        selection_add=[("Section", "Included in layout")],
        ondelete={"Section": "set default"},
    )
    layout_background_header_image = fields.Binary("Background Header Image")
    layout_background_footer_image = fields.Binary("Background Footer Image")

    layout_background_l_image = fields.Binary("Background Article Image-landscape")
    layout_background_l_header_image = fields.Binary("Background Header Image-landscape")
    layout_background_l_footer_image = fields.Binary("Background Footer Image-landscape")

    custom_scss_path = fields.Char("Custom SCSS Path")

    logo_print = fields.Binary("Logo print")
    font = fields.Selection(
        selection_add=[
            ("SF_Text", "SF Text"),
            ("SF_Pro_Text", "SF Text Pro"),
        ],
        ondelete={"SF_Text": "set default", "SF_Pro_Text": "set default"},
    )

    def get_custom_scss_content(self):
        """Прочита съдържанието на персонализирания SCSS файл от home директорията"""
        self.ensure_one()
        if not self.custom_scss_path:
            # Опитай се да намериш пътя, ако не е зададен
            self.custom_scss_path = get_scss_file_path(use_custom=True, company_id=self.id)

        if self.custom_scss_path and os.path.exists(self.custom_scss_path):
            try:
                with open(self.custom_scss_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    _logger.info(f"Loaded custom SCSS from: {self.custom_scss_path}")
                    return Markup(content)
            except Exception as e:
                _logger.error(f"Failed to read custom SCSS file: {e}")
        else:
            _logger.warning(f"Custom SCSS file not found: {self.custom_scss_path}")
        return Markup("")

    def get_layout_scss_content(self):
        """Прочита съдържанието на основните SCSS файлове на темата"""
        self.ensure_one()
        _logger.info(f"Generating layout SCSS for company {self.id}")

        scss_parts = []

        # 1. ПЪРВО: Зареди CUSTOM цветовете от home директорията (БЕЗ !default)
        custom_colors_path = get_scss_file_path(use_custom=True, company_id=self.id)
        if os.path.exists(custom_colors_path):
            try:
                with open(custom_colors_path, 'r', encoding='utf-8') as f:
                    custom_content = f.read()
                    # Премахни !default флаговете от custom файла
                    custom_content = custom_content.replace('!default', '').replace('  ;', ';')
                    indented = '\n'.join('    ' + line if line.strip() else line
                                         for line in custom_content.split('\n'))
                    scss_parts.append(f"    /* Custom colors from: {custom_colors_path} */\n{indented}")
                    _logger.info(f"Loaded custom colors from: {custom_colors_path}")
            except Exception as e:
                _logger.error(f"Failed to read custom colors file: {e}")
        else:
            _logger.warning(f"Custom colors file not found: {custom_colors_path}")

        # 2. СЛЕД ТОВА: Зареди останалите модулни файлове (БЕЗ report_variable_colors.scss)
        module_path = get_module_path('l10n_bg_report_theme')

        files = [
            # 'static/src/webclient/actions/reports/report_variable_colors.scss',  ← ПРЕМАХНАТО!
            'static/src/webclient/actions/reports/report_variable_fonts.scss',
            'static/src/webclient/actions/reports/default/report_variable_sizes.scss',
            'static/src/webclient/actions/reports/layout_assets/layout_background.scss',
            'static/src/webclient/actions/reports/layout_assets/layout_sections.scss',
        ]

        for file_path in files:
            full_path = os.path.join(module_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Индентираме съдържанието
                        indented = '\n'.join('    ' + line if line.strip() else line
                                             for line in content.split('\n'))
                        scss_parts.append(f"    /* {file_path} */\n{indented}")
                except Exception as e:
                    _logger.error(f"Failed to read theme SCSS file {file_path}: {e}")
            else:
                _logger.warning(f"SCSS file not found: {full_path}")

        # Обвиваме в компанийския клас
        wrapped = f".o_company_{self.id}_layout {{\n" + "\n\n".join(scss_parts) + "\n}"

        return Markup(wrapped)
