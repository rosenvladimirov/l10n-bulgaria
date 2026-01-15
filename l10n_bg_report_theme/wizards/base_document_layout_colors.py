import base64
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
    """Връща директорията за SCSS файловете в home директорията на потребителя"""
    home_dir = Path.home()
    scss_dir = home_dir / 'odoo_custom_scss'
    if not scss_dir.exists():
        scss_dir.mkdir(parents=True, exist_ok=True)
        # Задай правилни permissions за папката
        os.chmod(scss_dir, 0o755)
    return scss_dir


def get_scss_file_path(use_custom=True, company_id=None):
    """
    Връща пътя към SCSS файла.
    Args:
        use_custom: Ако True, използва персонализирания файл, иначе оригиналния от модула
        company_id: ИД на компанията за персонализирания файл
    """
    if use_custom:
        # Файл със специфично име за компанията в home директорията
        custom_dir = get_odoo_home_scss_dir()
        file_name = SCSS_FILE_NAME
        if company_id:
            file_name = f"report_variable_colors_{company_id}.scss"

        custom_file = custom_dir / file_name

        # Ако не съществува, копирай оригиналния като основа
        if not custom_file.exists():
            source_path = get_scss_file_path(use_custom=False)
            shutil.copy2(source_path, custom_file)
            os.chmod(custom_file, 0o644)

        return str(custom_file)
    else:
        # Оригинален файл от модула
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(module_path, *SCSS_MODULE_PATH)


def copy_scss_to_home(company_id=None):
    """Копира оригиналния SCSS файл в home директорията"""
    try:
        source_path = get_scss_file_path(use_custom=False)
        target_path = get_scss_file_path(use_custom=True, company_id=company_id)

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

    SCSS_VAR_FORMAT = SCSS_VAR_FORMAT

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
                # Актуализираме полето, за да се отрази в UI
                record.color_rgb = color_rgb
                # Запазваме във файла веднага
                self.save_scss_colors(record.name, record.color, color_rgb)
                # Опитваме се да предизвикаме преизчисляване на прегледа
                if record.base_document_layout_id:
                    record.base_document_layout_id._compute_preview()

    @api.model
    def load_scss_colors(self, force_dict=False, company_id=None):
        """Loads color variables from the SCSS file."""
        res = []
        res_dict = {}
        # Ако няма подаден company_id, опитай се да вземеш от контекста или текущата компания
        company_id = company_id or self.env.company.id
        scss_file_path = get_scss_file_path(use_custom=True, company_id=company_id)

        try:
            # Първо зареждаме оригиналния файл, за да имаме всички дефинирани цветове като структура
            original_path = get_scss_file_path(use_custom=False)
            with open(original_path, 'r', encoding='utf-8') as file:
                original_content = file.read()
                # pattern = r'\$([a-zA-Z-]+):\s*(rgb\(\d+,\s*\d+,\s*\d+\)|#[0-9a-fA-F]{3,6})(?:\s*!default)?\s*;'
                pattern = r'\$([a-zA-Z-]+):\s*([^;]+?)(?:\s*!default)?\s*;'
                original_matches = re.findall(pattern, original_content)
                for var_name, color_val in original_matches:
                    res_dict[var_name] = {
                        'name': var_name,
                        'color_val': color_val.strip()
                    }

            # След това зареждаме персонализирания файл и презаписваме стойностите
            if os.path.exists(scss_file_path):
                with open(scss_file_path, 'r', encoding='utf-8') as file:
                    custom_content = file.read()
                    custom_matches = re.findall(pattern, custom_content)
                    for var_name, color_val in custom_matches:
                        if var_name in res_dict:
                            res_dict[var_name]['color_val'] = color_val.strip()

            # Превръщаме в желания формат
            final_res_dict = {}
            for var_name, data in res_dict.items():
                color_val = data['color_val']
                if color_val.startswith('rgb'):
                    rgb_match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_val)
                    if rgb_match:
                        r, g, b = rgb_match.groups()
                        hex_color = "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))
                        rgb_value = f"rgb({r}, {g}, {b})"
                    else:
                        continue
                elif color_val.startswith('#'):
                    hex_color = color_val
                    rgb_value = _convert_hex_to_rgb(hex_color)
                else:
                    # Може да е референция към друга променлива или нещо друго, прескачаме за сега
                    continue

                res.append(Command.create({
                    'name': var_name,
                    'color': hex_color,
                    'color_rgb': rgb_value
                }))
                final_res_dict[var_name] = SCSS_VAR_FORMAT.format(var_name, rgb_value)

        except Exception as e:
            _logger.error("Failed to load SCSS colors: %s", str(e))

        return final_res_dict if force_dict else res

    @api.model
    def save_scss_colors(self, name=None, color=None, color_rgb=None, company_id=None):
        """Saves color variables to SCSS file."""
        try:
            name = name or self.name
            if not name:
                raise UserError("Color name is required")

            color_rgb = color_rgb or (color and _convert_hex_to_rgb(color))
            if not color_rgb:
                raise UserError("Color value is required")

            if company_id:
                company = self.env['res.company'].browse(company_id)
            else:
                company = self.base_document_layout_id.company_id or self.env.company

            scss_file_path = get_scss_file_path(use_custom=True, company_id=company.id)

            # Използваме load_scss_colors(force_dict=True), който вече зарежда и оригиналната структура
            color_records = self.load_scss_colors(force_dict=True, company_id=company.id)
            color_records[name] = SCSS_VAR_FORMAT.format(name, color_rgb)

            # Подреждаме ги по име за консистентност, или запазваме оригиналната подредба?
            # load_scss_colors зарежда от оригиналния файл, така че редът трябва да е горе-долу същият.
            scss_content = "/* colors */\n" + "".join(color_records.values())

            with open(scss_file_path, 'w', encoding='utf-8') as file:
                file.write(scss_content)

            # Запази пътя в компанията
            if company:
                company.custom_scss_path = scss_file_path
                # Актуализирай динамичния асет на Odoo 19.0
                if hasattr(company, '_update_asset_style'):
                    company._update_asset_style()
                # Инвалидиране на кеша на асетите за прегенериране на CSS
                self.env.registry.clear_cache('assets')

            _logger.info(f"Saved SCSS colors to: {scss_file_path}")

        except Exception as e:
            error_msg = f"Failed to save SCSS colors: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)

    def _update_ir_asset(self, company):
        """Този метод вече не се използва за файлове в home директорията,
        тъй като асет системата на Odoo няма достъп до тях директно.
        Разчитаме на инжектиране на съдържанието в QWeb шаблоните.
        """
        pass
