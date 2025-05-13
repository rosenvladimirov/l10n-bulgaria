import base64
import logging
import os
import re
from odoo import api, fields, models, Command
from webcolors import hex_to_rgb, rgb_to_hex

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Constants
SCSS_FILE_NAME = 'report_variable_colors.scss'
SCSS_FILE_PATH = ['static', 'src', 'webclient', 'actions', 'reports', SCSS_FILE_NAME]
RGB_FORMAT = "rgb({}, {}, {})"
SCSS_VAR_FORMAT = "${}: {};\n"


def get_scss_file_path():
    """Returns the full path to the SCSS file."""
    module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(module_path, *SCSS_FILE_PATH)


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
        """Loads color variables from the SCSS file."""
        res = []
        res_dict = {}
        scss_file_path = get_scss_file_path()

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
            _logger.warning("SCSS file not found at: %s", scss_file_path)
        except Exception as e:
            _logger.error("Failed to load SCSS file: %s", str(e))

        return res_dict if force_dict else res

    @api.model
    def save_scss_colors(self, name=None, color=None, color_rgb=None):
        """Saves color variables to SCSS file."""
        try:
            name = name or self.name
            if not name:
                raise UserError("Color name is required")

            color_rgb = color_rgb or (color and _convert_hex_to_rgb(color))
            if not color_rgb:
                raise UserError("Color value is required")

            scss_file_path = get_scss_file_path()
            color_records = self.load_scss_colors(force_dict=True)
            color_records[name] = SCSS_VAR_FORMAT.format(name, color_rgb)

            scss_content = "/* colors */\n" + "".join(color_records.values())
            with open(scss_file_path, 'w', encoding='utf-8') as file:
                file.write(scss_content)

        except Exception as e:
            error_msg = f"Failed to save SCSS colors: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)
