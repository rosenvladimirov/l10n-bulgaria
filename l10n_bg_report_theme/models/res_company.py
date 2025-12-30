#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os

from odoo import fields, models
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
        """Връща съдържанието на персонализирания SCSS файл с цветове"""
        path = self.custom_scss_path or get_scss_file_path(use_custom=True)
        if not path or not os.path.exists(path):
            return ""
        try:
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            _logger.warning(f"Could not read custom SCSS file at {path}: {e}")
            return ""
