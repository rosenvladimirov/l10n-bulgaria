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
                    _logger.info(f"✓ get_custom_scss_content() loaded from: {self.custom_scss_path}")
                    return Markup(content)
            except Exception as e:
                _logger.error(f"✗ get_custom_scss_content() failed: {e}")
        else:
            _logger.warning(f"✗ get_custom_scss_content() NOT FOUND: {self.custom_scss_path}")
        return Markup("")

    def get_layout_scss_content(self):
        """Прочита съдържанието на основните SCSS файлове на темата"""
        self.ensure_one()
        _logger.info(f"=" * 80)
        _logger.info(f"🎨 Generating layout SCSS for company ID: {self.id}")
        _logger.info(f"🏢 Company name: {self.name}")
        _logger.info(f"=" * 80)

        scss_parts = []

        # 1. ПЪРВО: Зареди CUSTOM цветовете от home директорията (БЕЗ !default)
        custom_colors_path = get_scss_file_path(use_custom=True, company_id=self.id)
        _logger.info(f"📁 Looking for custom colors at: {custom_colors_path}")
        _logger.info(f"   File exists: {os.path.exists(custom_colors_path)}")

        if os.path.exists(custom_colors_path):
            try:
                with open(custom_colors_path, 'r', encoding='utf-8') as f:
                    custom_content = f.read()
                    _logger.info(f"📄 Custom SCSS file size: {len(custom_content)} chars")
                    _logger.info(f"📄 First 300 chars:\n{custom_content[:300]}")

                    # Премахни !default флаговете от custom файла
                    custom_content = custom_content.replace('!default', '').replace('  ;', ';')

                    # Индентираме само непразните редове
                    lines = []
                    for line in custom_content.split('\n'):
                        if line.strip():  # Ако реда не е празен
                            lines.append('    ' + line)
                        else:  # Празен ред остава празен
                            lines.append('')

                    indented = '\n'.join(lines)
                    scss_parts.append(f"    /* Custom colors from: {custom_colors_path} */\n{indented}")
                    _logger.info(f"✅ Successfully loaded custom colors")
            except Exception as e:
                _logger.error(f"❌ Failed to read custom colors file: {e}", exc_info=True)
        else:
            _logger.warning(f"⚠️  Custom colors file NOT FOUND: {custom_colors_path}")

        # 2. СЛЕД ТОВА: Зареди останалите модулни файлове
        module_path = get_module_path('l10n_bg_report_theme')
        _logger.info(f"-" * 80)
        _logger.info(f"📦 Module path: {module_path}")
        _logger.info(f"-" * 80)

        files = [
            'static/src/webclient/actions/reports/report_variable_fonts.scss',
            'static/src/webclient/actions/reports/report_variable_sizes.scss',
            'static/src/webclient/actions/reports/layout_assets/layout_background.scss',
            'static/src/webclient/actions/reports/layout_assets/layout_sections.scss',
        ]

        for idx, file_path in enumerate(files, start=2):
            full_path = os.path.join(module_path, file_path)
            _logger.info(f"📂 [{idx}] Loading: {file_path}")
            _logger.info(f"   Full path: {full_path}")
            _logger.info(f"   Exists: {os.path.exists(full_path)}")

            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        _logger.info(f"   Size: {len(content)} chars")

                        # Индентираме само непразните редове
                        lines = []
                        for line in content.split('\n'):
                            if line.strip():  # Ако реда не е празен
                                lines.append('    ' + line)
                            else:  # Празен ред остава празен
                                lines.append('')

                        indented = '\n'.join(lines)
                        scss_parts.append(f"    /* {file_path} */\n{indented}")
                        _logger.info(f"   ✅ Successfully loaded")
                except Exception as e:
                    _logger.error(f"   ❌ Failed to read: {e}", exc_info=True)
            else:
                _logger.warning(f"   ⚠️  File NOT FOUND")

        # Обвиваме в компанийския клас
        wrapped = f".o_company_{self.id}_layout {{\n" + "\n\n".join(scss_parts) + "\n}}"

        _logger.info(f"=" * 80)
        _logger.info(f"📊 SCSS Generation Summary:")
        _logger.info(f"   Total SCSS parts: {len(scss_parts)}")
        _logger.info(f"   Total characters: {len(wrapped)}")
        _logger.info(f"   Wrapper class: .o_company_{self.id}_layout")
        _logger.info(f"=" * 80)

        # DEBUG: Запиши генерирания SCSS в temp файл
        try:
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.scss', delete=False, encoding='utf-8')
            temp_file.write(wrapped)
            temp_file.close()
            _logger.info(f"💾 Generated SCSS saved to: {temp_file.name}")
            _logger.info(f"   You can inspect with: cat {temp_file.name}")
            _logger.info(f"   Or check syntax with: sass {temp_file.name}")
        except Exception as e:
            _logger.warning(f"⚠️  Could not save debug SCSS file: {e}")

        # Покажи първите 1000 символа от генерирания SCSS
        _logger.info(f"-" * 80)
        _logger.info(f"📝 First 1000 chars of generated SCSS:")
        _logger.info(f"-" * 80)
        _logger.info(f"\n{wrapped[:1000]}\n")
        _logger.info(f"-" * 80)

        # Покажи и последните 500 символа (където е грешката)
        _logger.info(f"📝 Last 500 chars of generated SCSS:")
        _logger.info(f"-" * 80)
        _logger.info(f"\n{wrapped[-500:]}\n")
        _logger.info(f"=" * 80)

        return Markup(wrapped)
