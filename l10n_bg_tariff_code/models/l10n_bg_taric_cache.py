# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import io
import re
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class L10nBgTaricCache(models.Model):
    """Локален кеш на TARIC тарифни ставки от CIRCABC данни"""
    _name = 'l10n_bg.taric.cache'
    _description = 'TARIC Tariff Rate Cache'
    _rec_name = 'cn_code'
    _order = 'cn_code, country_code'

    cn_code = fields.Char(
        string='CN Code',
        required=True,
        index=True,
        help="Combined Nomenclature code (8-10 digits)"
    )

    country_code = fields.Char(
        string='Country Code',
        required=True,
        index=True,
        help="ISO country code (e.g., CN, US, etc.)"
    )

    duty_rate = fields.Float(
        string='Duty Rate (%)',
        required=True,
        help="Customs duty rate in percentage"
    )

    measure_type = fields.Char(
        string='Measure Type',
        help="Type of measure (e.g., 103 = Third country duty)"
    )

    description = fields.Text(
        string='Description',
        help="Goods nomenclature description"
    )

    valid_from = fields.Date(
        string='Valid From',
        required=True,
        index=True,
        default=fields.Date.today
    )

    valid_to = fields.Date(
        string='Valid To',
        required=True,
        index=True,
        default=lambda self: fields.Date.today() + timedelta(days=365)
    )

    source = fields.Selection([
        ('api', 'API'),
        ('circabc', 'CIRCABC Import'),
        ('manual', 'Manual Entry'),
    ], string='Data Source', default='api', required=True)

    last_update = fields.Datetime(
        string='Last Update',
        default=fields.Datetime.now,
        required=True
    )

    _unique_taric_entry = models.Constraint(
        'unique (cn_code, country_code, valid_from, valid_to)',
        "TARIC entry must be unique per code, country and validity period!",
    )

    @api.model
    def import_from_circabc_url(self, file_url):
        """
        Импортира TARIC данни директно от CIRCABC URL

        Примерни URLs:
        - https://circabc.europa.eu/sd/a/[file-id]/TARIC_data.xlsx
        - https://circabc.europa.eu/d/d/workspace/...
        """
        try:
            _logger.info(f"Downloading TARIC data from CIRCABC: {file_url}")

            headers = {
                'User-Agent': 'Odoo-BG-Tariff/2.0',
            }

            response = requests.get(file_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Определяме типа на файла
            content_type = response.headers.get('content-type', '').lower()

            if 'excel' in content_type or 'spreadsheet' in content_type or file_url.endswith('.xlsx'):
                return self._import_from_excel(io.BytesIO(response.content))
            elif 'csv' in content_type or file_url.endswith('.csv'):
                return self._import_from_csv(io.StringIO(response.text))
            else:
                raise UserError(_("Unsupported file format. Only Excel (.xlsx) and CSV files are supported."))

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error downloading CIRCABC file: {e}")
            raise UserError(_("Failed to download TARIC data from CIRCABC: %s") % str(e))

    @api.model
    def import_from_file(self, file_data, filename):
        """
        Импортира TARIC данни от качен файл

        :param file_data: base64 encoded file content
        :param filename: name of the file
        """
        import base64

        try:
            decoded_data = base64.b64decode(file_data)

            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                return self._import_from_excel(io.BytesIO(decoded_data))
            elif filename.endswith('.csv'):
                return self._import_from_csv(io.StringIO(decoded_data.decode('utf-8')))
            else:
                raise UserError(_("Unsupported file format. Only Excel (.xlsx) and CSV files are supported."))

        except Exception as e:
            _logger.error(f"Error importing TARIC file: {e}")
            raise UserError(_("Failed to import TARIC data: %s") % str(e))

    def _import_from_excel(self, file_stream):
        """Импортира данни от Excel файл"""
        try:
            # Изисква openpyxl или xlrd
            try:
                import openpyxl
                workbook = openpyxl.load_workbook(file_stream)
                sheet = workbook.active

                # Конвертираме в списък от редове
                rows = list(sheet.values)

            except ImportError:
                try:
                    import xlrd
                    workbook = xlrd.open_workbook(file_contents=file_stream.read())
                    sheet = workbook.sheet_by_index(0)
                    rows = [sheet.row_values(i) for i in range(sheet.nrows)]
                except ImportError:
                    raise UserError(_("Please install 'openpyxl' or 'xlrd' package: pip install openpyxl"))

            return self._process_taric_rows(rows)

        except Exception as e:
            _logger.error(f"Error reading Excel file: {e}")
            raise UserError(_("Failed to read Excel file: %s") % str(e))

    def _import_from_csv(self, file_stream):
        """Импортира данни от CSV файл"""
        try:
            csv_reader = csv.reader(file_stream)
            rows = list(csv_reader)
            return self._process_taric_rows(rows)

        except Exception as e:
            _logger.error(f"Error reading CSV file: {e}")
            raise UserError(_("Failed to read CSV file: %s") % str(e))

    def _process_taric_rows(self, rows):
        """
        Обработва редовете от TARIC файл

        Очакван формат на колоните:
        - CN Code (8-10 digits)
        - Country Code (2 chars) or Geographical Area
        - Duty Rate (number with %)
        - Description (optional)
        - Valid From (date, optional)
        - Valid To (date, optional)
        """
        if not rows:
            raise UserError(_("File is empty"))

        # Откриваме header реда
        header_row = rows[0]
        header_mapping = self._map_headers(header_row)

        if not header_mapping:
            raise UserError(_("Could not identify required columns. Expected: CN Code, Country, Duty Rate"))

        imported_count = 0
        updated_count = 0
        error_count = 0

        for row_idx, row in enumerate(rows[1:], start=2):
            try:
                if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                    continue

                taric_data = self._extract_row_data(row, header_mapping)

                if not taric_data:
                    continue

                # Търсим съществуващ запис
                existing = self.search([
                    ('cn_code', '=', taric_data['cn_code']),
                    ('country_code', '=', taric_data['country_code']),
                    ('valid_from', '<=', taric_data['valid_to']),
                    ('valid_to', '>=', taric_data['valid_from']),
                ])

                if existing:
                    existing.write({
                        'duty_rate': taric_data['duty_rate'],
                        'description': taric_data.get('description'),
                        'measure_type': taric_data.get('measure_type'),
                        'valid_to': taric_data['valid_to'],
                        'last_update': fields.Datetime.now(),
                        'source': 'circabc',
                    })
                    updated_count += 1
                else:
                    self.create({
                        **taric_data,
                        'source': 'circabc',
                        'last_update': fields.Datetime.now(),
                    })
                    imported_count += 1

            except Exception as e:
                _logger.warning(f"Error processing row {row_idx}: {e}")
                error_count += 1
                continue

        message = _("Import completed:\n- New records: %d\n- Updated records: %d\n- Errors: %d") % (
            imported_count, updated_count, error_count
        )

        _logger.info(message)
        return {
            'imported': imported_count,
            'updated': updated_count,
            'errors': error_count,
            'message': message,
        }

    def _map_headers(self, header_row):
        """Мапва колоните от header реда"""
        mapping = {}

        for idx, cell in enumerate(header_row):
            cell_str = str(cell).lower().strip()

            # CN Code
            if any(x in cell_str for x in ['cn', 'code', 'commodity', 'nomenclature', 'taric']):
                if 'cn' in cell_str or 'code' in cell_str:
                    mapping['cn_code'] = idx

            # Country
            elif any(x in cell_str for x in ['country', 'origin', 'geographical', 'geo']):
                mapping['country_code'] = idx

            # Duty Rate
            elif any(x in cell_str for x in ['duty', 'rate', 'tariff', '%', 'percent']):
                mapping['duty_rate'] = idx

            # Description
            elif any(x in cell_str for x in ['description', 'desc', 'goods', 'product']):
                mapping['description'] = idx

            # Measure Type
            elif any(x in cell_str for x in ['measure', 'type']):
                mapping['measure_type'] = idx

            # Valid From
            elif any(x in cell_str for x in ['valid from', 'start', 'from date', 'effective']):
                mapping['valid_from'] = idx

            # Valid To
            elif any(x in cell_str for x in ['valid to', 'end', 'to date', 'expiry']):
                mapping['valid_to'] = idx

        # Проверяваме дали имаме минималните колони
        if 'cn_code' in mapping and 'duty_rate' in mapping:
            return mapping

        return None

    def _extract_row_data(self, row, header_mapping):
        """Извлича данните от ред"""
        try:
            # CN Code (задължително)
            cn_code_raw = str(row[header_mapping['cn_code']]).strip()
            cn_code = self._normalize_cn_code(cn_code_raw)

            if not cn_code or len(cn_code) < 6:
                return None

            # Duty Rate (задължително)
            duty_rate_raw = str(row[header_mapping['duty_rate']])
            duty_rate = self._parse_duty_rate(duty_rate_raw)

            if duty_rate is None:
                return None

            # Country Code
            country_code = 'CN'  # default
            if 'country_code' in header_mapping:
                country_raw = str(row[header_mapping['country_code']]).strip().upper()
                # Извличаме ISO кода (първите 2 символа)
                if len(country_raw) >= 2:
                    country_code = country_raw[:2]

            # Description
            description = ''
            if 'description' in header_mapping:
                description = str(row[header_mapping['description']]).strip()

            # Measure Type
            measure_type = '103'  # default = Third country duty
            if 'measure_type' in header_mapping:
                measure_type = str(row[header_mapping['measure_type']]).strip()

            # Valid From/To
            valid_from = fields.Date.today()
            if 'valid_from' in header_mapping:
                valid_from = self._parse_date(row[header_mapping['valid_from']])

            valid_to = valid_from + timedelta(days=365)
            if 'valid_to' in header_mapping:
                parsed_to = self._parse_date(row[header_mapping['valid_to']])
                if parsed_to:
                    valid_to = parsed_to

            return {
                'cn_code': cn_code,
                'country_code': country_code,
                'duty_rate': duty_rate,
                'description': description,
                'measure_type': measure_type,
                'valid_from': valid_from,
                'valid_to': valid_to,
            }

        except Exception as e:
            _logger.warning(f"Error extracting row data: {e}")
            return None

    def _normalize_cn_code(self, code_raw):
        """Нормализира CN кода"""
        # Премахваме всички не-цифри
        digits = ''.join(filter(str.isdigit, code_raw))

        if len(digits) < 6:
            return None
        elif len(digits) == 6:
            return digits + '00'  # HS -> CN
        elif len(digits) == 8:
            return digits
        elif len(digits) >= 10:
            return digits[:10]
        else:
            # 7 или 9 цифри - padding
            return digits.ljust(10, '0')

    def _parse_duty_rate(self, rate_raw):
        """Извлича числовата стойност на duty rate"""
        try:
            # Премахваме всички символи освен цифри, точка и минус
            cleaned = re.sub(r'[^\d.\-]', '', str(rate_raw))

            if not cleaned or cleaned == '-':
                return None

            rate = float(cleaned)

            # Ако е над 100, вероятно е в basis points
            if rate > 100:
                rate = rate / 100

            return rate

        except (ValueError, TypeError):
            return None

    def _parse_date(self, date_value):
        """Парсва дата от различни формати"""
        if not date_value:
            return None

        try:
            # Ако е вече datetime обект
            if isinstance(date_value, datetime):
                return date_value.date()

            # Ако е string
            date_str = str(date_value).strip()

            # Опитваме различни формати
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue

        except Exception:
            pass

        return None

    @api.model
    def cleanup_expired_entries(self):
        """Изчиства изтекли записи (извиква се от cron)"""
        expired = self.search([
            ('valid_to', '<', fields.Date.today() - timedelta(days=30))
        ])

        count = len(expired)
        expired.unlink()

        _logger.info(f"Cleaned up {count} expired TARIC entries")
        return count
