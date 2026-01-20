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
            scss_path = get_scss_file_path(use_custom=True, company_id=self.id)
            if os.path.exists(scss_path):
                self.custom_scss_path = scss_path

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
        _logger.info(f"=" * 80)

        scss_parts = []

        # 1. ПЪРВО: Зареди CUSTOM цветовете от home директорията (БЕЗ !default)
        custom_colors_path = get_scss_file_path(use_custom=True, company_id=self.id)

        if os.path.exists(custom_colors_path):
            try:
                with open(custom_colors_path, 'r', encoding='utf-8') as f:
                    custom_content = f.read()

                    # Премахни !default флаговете
                    custom_content = custom_content.replace('!default', '').replace('  ;', ';')

                    # Добави коментар и съдържанието без допълнителна индентация
                    scss_parts.append(f"/* Custom colors from: {custom_colors_path} */\n{custom_content}")
                    _logger.info(f"✅ Loaded custom colors ({len(custom_content)} chars)")
            except Exception as e:
                _logger.error(f"❌ Failed to read custom colors: {e}")
        else:
            _logger.warning(f"⚠️  Custom colors NOT FOUND: {custom_colors_path}")

        # 2. СЛЕД ТОВА: Зареди останалите модулни файлове
        module_path = get_module_path('l10n_bg_report_theme')

        files = [
            'static/src/webclient/actions/reports/report_variable_fonts.scss',
            'static/src/webclient/actions/reports/report_variable_sizes.scss',
            'static/src/webclient/actions/reports/layout_assets/layout_background.scss',
            'static/src/webclient/actions/reports/layout_assets/layout_sections.scss',
        ]

        for file_path in files:
            full_path = os.path.join(module_path, file_path)

            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                        # Провери баланса на скобите
                        open_braces = content.count('{')
                        close_braces = content.count('}')

                        if open_braces != close_braces:
                            _logger.warning(
                                f"⚠️  Unbalanced braces in {file_path}: {{={open_braces}, }}={close_braces}")

                        # Добави коментар и съдържанието без допълнителна индентация
                        scss_parts.append(f"/* {file_path} */\n{content}")
                        _logger.info(
                            f"✅ Loaded {file_path} ({len(content)} chars, braces: {open_braces}/{close_braces})")
                except Exception as e:
                    _logger.error(f"❌ Failed to read {file_path}: {e}")
            else:
                _logger.warning(f"⚠️  NOT FOUND: {full_path}")

        # ВАЖНО: НЕ обвиваме в .o_company_{id}_layout !
        # Wrapper-ът се добавя от XML template-а!
        # Но добавяме селектор, за да сме сигурни, че важи за компанията,
        # ако Odoo го инжектира глобално.
        # Всъщност в styles_company_report_sections го инжектираме само за съответната компания.

        # За да сме сигурни, че се преизчислява прегледа, добавяме timestamp или нещо уникално като коментар
        import datetime
        scss_parts.insert(0, f"/* Generated at: {datetime.datetime.now()} */")

        wrapped = "\n\n".join(scss_parts)

        # Провери общия баланс
        total_open = wrapped.count('{')
        total_close = wrapped.count('}')
        _logger.info(f"📊 Total braces: {{={total_open}, }}={total_close}")

        if total_open != total_close:
            _logger.error(f"❌ UNBALANCED BRACES! Difference: {total_open - total_close}")

        # DEBUG: Запиши
        try:
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.scss', delete=False, encoding='utf-8')
            temp_file.write(wrapped)
            temp_file.close()
            _logger.info(f"💾 Saved to: {temp_file.name}")
        except:
            pass

        return Markup(wrapped)
