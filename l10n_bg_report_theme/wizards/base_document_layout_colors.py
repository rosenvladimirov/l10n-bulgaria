#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import re
import shutil
from pathlib import Path
from odoo import api, fields, models, Command
from odoo.tools import config
from webcolors import hex_to_rgb, rgb_to_hex
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Constants
SCSS_FILE_NAME = 'report_variable_colors.scss'
SCSS_MODULE_PATH = ['static', 'src', 'webclient', 'actions', 'reports', SCSS_FILE_NAME]
RGB_FORMAT = "rgb({}, {}, {})"
SCSS_VAR_FORMAT = "${}: {};\n"


def get_odoo_home_scss_dir():
    """Връща home директорията за SCSS файловете на Odoo потребителя"""
    # Опитай се да вземеш от config, иначе използвай home
    custom_path = config.get('custom_scss_path')
    if custom_path:
        base_path = Path(custom_path)
    else:
        base_path = Path.home() / 'odoo_custom_scss'

    scss_dir = base_path / 'l10n_bg_report_theme'
    scss_dir.mkdir(parents=True, exist_ok=True)
    return scss_dir


def get_scss_file_path(use_custom=True):
    """
    Връща пътя към SCSS файла.
    Args:
        use_custom: Ако True, използва файла от home, иначе от модула
    """
    if use_custom:
        # Файл от home директорията
        custom_dir = get_odoo_home_scss_dir()
        custom_file = custom_dir / SCSS_FILE_NAME

        # Ако не съществува в home, копирай го от модула
        if not custom_file.exists():
            _logger.info(f"Custom SCSS not found, copying from module to {custom_file}")
            copy_scss_to_home()

        return str(custom_file)
    else:
        # Оригинален файл от модула
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(module_path, *SCSS_MODULE_PATH)


def copy_scss_to_home():
    """Копира оригиналния SCSS файл в home директорията"""
    try:
        source_path = get_scss_file_path(use_custom=False)
        target_dir = get_odoo_home_scss_dir()
        target_path = target_dir / SCSS_FILE_NAME

        if not Path(source_path).exists():
            _logger.error(f"Source SCSS file not found: {source_path}")
            return False

        # Копирай файла
        shutil.copy2(source_path, target_path)
        _logger.info(f"Copied SCSS file from {source_path} to {target_path}")

        # Задай правилни permissions
        os.chmod(target_path, 0o644)

        return True

    except Exception as e:
        _logger.error(f"Failed to copy SCSS file to home: {e}")
        return False


def _convert_hex_to_rgb(hex_color):
    """Helper function to convert HEX color to RGB format."""
    try:
        color_hex = hex_to_rgb(hex_color)
        return RGB_FORMAT.format(color_hex.red, color_hex.green, color_hex.blue)
    except ValueError as e:
        raise UserError(f"Invalid color format: {hex_color}") from e

class DocumentLayoutColorManager(models.TransientModel):
    _name = 'base.document.layout.colors'
    _description = 'Document Layout Colors Configuration'

    name = fields.Char(string="Name")
    color = fields.Char(string="Color")
    color_rgb = fields.Char(string="Color RGB", compute="_compute_color_rgb")
    base_document_layout_id = fields.Many2one('base.document.layout', string="Layout", ondelete='cascade')

    def _compute_color_rgb(self):
        for record in self:
            if record.color:
                record.color_rgb = _convert_hex_to_rgb(record.color)
            else:
                record.color_rgb = False

    @api.onchange('color')
    def _onchange_color(self):
        for record in self:
            if record.color and record.name:
                color_rgb = _convert_hex_to_rgb(record.color)
                self.save_scss_colors(record.name, record.color, color_rgb)
                self.base_document_layout_id._compute_preview()

    @api.model
    def load_scss_colors(self, force_dict=False):
        """Loads color variables from the SCSS file (from the home directory)."""
        res = []
        res_dict = {}
        scss_file_path = get_scss_file_path(use_custom=True)  # Винаги чете от home

        try:
            with open(scss_file_path, 'r', encoding='utf-8') as file:
                scss_content = file.read()
                pattern = r'\$([a-zA-Z-]+):\s*rgb\((\d+),\s*(\d+),\s*(\d+)\);'
                matches = re.findall(pattern, scss_content)

                for var_name, r, g, b in matches:
                    hex_color = "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))
                    rgb_value = RGB_FORMAT.format(r, g, b)

                    res.append(Command.create({
                        'name': var_name,
                        'color': hex_color,
                        'color_rgb': rgb_value
                    }))
                    res_dict[var_name] = SCSS_VAR_FORMAT.format(var_name, rgb_value)

        except FileNotFoundError:
            _logger.warning("SCSS file not found at: %s. Copying from module...", scss_file_path)
            copy_scss_to_home()
            # Опитай отново след копиране
            return self.load_scss_colors(force_dict=force_dict)
        except Exception as e:
            _logger.error("Failed to load SCSS file: %s", str(e))

        return res_dict if force_dict else res

    @api.model
    def save_scss_colors(self, name=None, color=None, color_rgb=None):
        """Saves color variables to SCSS file in the home directory."""
        try:
            name = name or self.name
            if not name:
                raise UserError("Color name is required")

            color_rgb = color_rgb or (color and _convert_hex_to_rgb(color))
            if not color_rgb:
                raise UserError("Color value is required")

            scss_file_path = get_scss_file_path(use_custom=True)  # Винаги пише в home
            color_records = self.load_scss_colors(force_dict=True)
            color_records[name] = SCSS_VAR_FORMAT.format(name, color_rgb)

            scss_content = "/* colors */\n" + "".join(color_records.values())

            with open(scss_file_path, 'w', encoding='utf-8') as file:
                file.write(scss_content)

            # Запази пътя в компанията
            company = self.base_document_layout_id.company_id or self.env.company
            if company:
                company.custom_scss_path = scss_file_path
                # Инвалидиране на кеша на асетите за прегенериране на CSS
                self.env.registry.clear_cache('assets')

            _logger.info(f"Saved SCSS colors to: {scss_file_path}")

        except Exception as e:
            error_msg = f"Failed to save SCSS colors: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)

    def _update_asset_content(self, content):
        """Deprecated: Актуализира ir.asset записа с новото съдържание на SCSS"""
        return
