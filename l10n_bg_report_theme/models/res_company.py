#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
from markupsafe import Markup

from odoo import fields, models
from odoo.modules import get_module_resource
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
                    return Markup(content)
            except Exception as e:
                _logger.error(f"Failed to read custom SCSS file: {e}")
        return Markup("")

    def get_layout_scss_content(self):
        """Прочита съдържанието на основните SCSS файлове на темата"""
        _logger.info(f"Generating layout SCSS for company {self.id}")
        contents = []
        files = [
            ('l10n_bg_report_theme', 'static/src/webclient/actions/reports/report_variable_colors.scss'),
            ('l10n_bg_report_theme', 'static/src/webclient/actions/reports/report_variable_fonts.scss'),
            ('l10n_bg_report_theme', 'static/src/webclient/actions/reports/default/report_variable_sizes.scss'),
            ('l10n_bg_report_theme', 'static/src/webclient/actions/reports/layout_assets/layout_background.scss'),
            ('l10n_bg_report_theme', 'static/src/webclient/actions/reports/layout_assets/layout_sections.scss'),
        ]
        for module, path in files:
            full_path = get_module_resource(module, *path.split('/'))
            if full_path and os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        contents.append(f"/* {path} */\n" + f.read())
                except Exception as e:
                    _logger.error(f"Failed to read theme SCSS file {path}: {e}")

        return Markup("\n".join(contents))
