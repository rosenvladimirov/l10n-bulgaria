
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
from datetime import datetime

from odoo import models, fields, api
import requests
import logging
import re

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Тарифен код с backward compatibility за HS/CN/Intrastat
    l10n_bg_tariff_code = fields.Char(
        string='Tariff/HS/CN Code',
        compute='_compute_l10n_bg_tariff_code',
        inverse='_inverse_l10n_bg_tariff_code',
        store=True,
        help="Tariff code (CN/HS/intrastat compatible)"
    )

    l10n_bg_tariff_code_manual = fields.Char(
        string='Manual Tariff Code',
        help="Manually entered tariff code"
    )

    # ТАРИК ставка с compute/inverse/store
    l10n_bg_tariff_rate = fields.Float(
        string='Tariff Rate (%)',
        compute='_compute_l10n_bg_tariff_rate',
        inverse='_inverse_l10n_bg_tariff_rate',
        store=True,
        help="Tariff rate from the EU Taric System"
    )

    l10n_bg_tariff_rate_manual = fields.Float(
        string='Manual Tariff Rate (%)',
        help="Manually entered tariff rate"
    )

    l10n_bg_tariff_rate_is_manual = fields.Boolean(
        string='Manual Rate Override',
        default=False,
        help="Indicates whether the rate is manually entered and should not be recalculated automatically"
    )

    l10n_bg_tariff_description = fields.Text(
        string='Tariff Description',
        help="Description from the TARIC system"
    )

    l10n_bg_tariff_last_update = fields.Datetime(
        string='Tariff Last Update',
        help="Last tariff rate update"
    )

    def _get_tariff_code_from_intrastat(self, product):
        """Метод за извличане на тарифен код от intrastat система

        Този метод е предназначен за override в други модули
        които имплементират интеграция с intrastat системата.
        """
        return False

    @api.depends('product_id', 'name', 'l10n_bg_tariff_code_manual')
    def _compute_l10n_bg_tariff_code(self):
        """Извлича тарифния код с backward compatibility за HS и Intrastat"""
        for line in self:
            tariff_code = False

            # Пропускаме ако няма продукт или е невалиден
            if line.product_id:
                # Проверка за реален ID (не NewId) и съществуване
                if isinstance(line.product_id.id, int) and not line.product_id.exists():
                    _logger.warning(f"Продуктът за ред {line.id} не съществува")
                    line.l10n_bg_tariff_code = False
                    continue

            # 1. Първо проверяваме ръчно въведения код
            if line.l10n_bg_tariff_code_manual:
                tariff_code = line._normalize_tariff_code(line.l10n_bg_tariff_code_manual)

            # 2. HS Code от stock_delivery модула (приоритет)
            if not tariff_code and line.product_id and hasattr(line.product_id, 'hs_code') and line.product_id.hs_code:
                normalized = line._normalize_tariff_code(line.product_id.hs_code)
                if normalized:
                    tariff_code = normalized

            # 3. Опит за извличане от intrastat (чрез override метод)
            if not tariff_code and line.product_id:
                intrastat_code = line._get_tariff_code_from_intrastat(line.product_id)
                if intrastat_code:
                    normalized = line._normalize_tariff_code(intrastat_code)
                    if normalized:
                        tariff_code = normalized.ljust(10, '0')

            # 4. Търсим в описанието на реда
            if not tariff_code and line.name:
                tariff_code = line._extract_code_from_text(line.name)

            # 5. Fallback към категорията на продукта
            if not tariff_code and line.product_id and line.product_id.categ_id:
                tariff_code = line._get_category_tariff_code(line.product_id.categ_id)

            line.l10n_bg_tariff_code = tariff_code

    def _inverse_l10n_bg_tariff_code(self):
        """Позволява ръчно задаване на тарифен код"""
        for line in self:
            if line.l10n_bg_tariff_code:
                normalized = line._normalize_tariff_code(line.l10n_bg_tariff_code)
                line.l10n_bg_tariff_code_manual = normalized

                # Ако имаме продукт и той няма HS код, опитваме се да го обновим
                if (line.product_id
                    and isinstance(line.product_id.id, int)
                    and line.product_id.exists()
                    and hasattr(line.product_id, 'hs_code')
                    and not line.product_id.hs_code
                    and normalized and len(normalized) >= 6):
                    try:
                        line.product_id.sudo().write({'hs_code': normalized})
                        _logger.info(f"Updated HS code of a product {line.product_id.name}: {normalized}")
                    except Exception as e:
                        _logger.warning(f"Unable to update product HS code: {e}")

    def _normalize_tariff_code(self, code_input):
        """Нормализира тарифния код от различни формати"""
        if not code_input:
            return False

        # Премахваме всички символи освен цифрите
        digits_only = "".join(filter(str.isdigit, str(code_input).upper()))

        if not digits_only:
            return False

        # Валидираме дължината
        if len(digits_only) < 6:  # Минимум за HS код
            return False
        elif len(digits_only) == 6:  # HS код - допълваме до CN
            return digits_only + "00"
        elif len(digits_only) == 8:  # CN код
            return digits_only
        elif len(digits_only) >= 10:  # Пълен код с подкатегории
            return digits_only[:10]
        else:
            # 7 или 9 цифри - допълваме до най-близкия стандарт
            if len(digits_only) == 7:
                return digits_only + "0"
            else:  # 9 цифри
                return digits_only + "0"

        return digits_only

    def _extract_code_from_text(self, text):
        """Извлича тарифен/HS/CN код от текст с различни формати"""
        if not text:
            return False

        patterns = [
            r'CN:?\s*(\d{8,10})',
            r'HS:?\s*(\d{6,10})',
            r'code:?\s*(\d{6,10})',
            r'intrastat:?\s*(\d{8})',
            r'tariff:?\s*(\d{6,10})',
            r'commodity:?\s*(\d{6,10})',
            r'(\d{8,10})(?=\s|$|[^\d])',
            r'(\d{6})(?=\s|$|[^\d])',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = self._normalize_tariff_code(match)
                if normalized:
                    return normalized

        return False

    def _get_category_tariff_code(self, category):
        """Извлича тарифен код на базата на категорията на продукта"""
        if not category:
            return False

        if category.name:
            code = self._extract_code_from_text(category.name)
            if code:
                return code

        if category.parent_id:
            return self._get_category_tariff_code(category.parent_id)

        return False

    @api.depends('l10n_bg_tariff_code', 'product_id', 'l10n_bg_tariff_rate_manual')
    def _compute_l10n_bg_tariff_rate(self):
        """Автоматично търси тарифната ставка в ЕС ТАРИК използвайки REST API"""
        for line in self:
            # Ако има ръчно въведена ставка, използваме нея
            if line.l10n_bg_tariff_rate_manual:
                line.l10n_bg_tariff_rate = line.l10n_bg_tariff_rate_manual
                continue

            # Пропускаме автоматично преизчисляване ако е маркирано като ръчно
            if line.l10n_bg_tariff_rate_is_manual:
                continue

            # Защита срещу изтрити записи
            if line.product_id and isinstance(line.product_id.id, int) and not line.product_id.exists():
                _logger.warning(f"The row product {line.id} does not exist")
                line.l10n_bg_tariff_rate = 0.0
                continue

            if not line.l10n_bg_tariff_code:
                line.l10n_bg_tariff_rate = 0.0
                continue

            # Проверяваме дали имаме кеширана стойност
            company = line.company_id or self.env.company
            cache_duration = company.l10n_bg_taric_cache_duration * 3600

            if (line.l10n_bg_tariff_last_update and
                line.l10n_bg_tariff_rate is not False and
                (fields.Datetime.now() - line.l10n_bg_tariff_last_update).total_seconds() < cache_duration):
                continue

            if not company.l10n_bg_taric_api_enabled:
                if not line.l10n_bg_tariff_rate:
                    # Нормализираме company default rate
                    default_rate = company.l10n_bg_default_tariff_rate
                    if default_rate > 1:
                        default_rate = default_rate / 100.0
                    line.l10n_bg_tariff_rate = default_rate
                continue

            try:
                search_code = line.l10n_bg_tariff_code[:8] if len(
                    line.l10n_bg_tariff_code) >= 8 else line.l10n_bg_tariff_code.ljust(8, '0')

                # Използваме country_of_origin от продукта
                country_code = 'CN'  # по подразбиране
                if line.product_id and hasattr(line.product_id,
                                               'country_of_origin') and line.product_id.country_of_origin:
                    country_code = line.product_id.country_of_origin.code
                if self.env.company.l10n_bg_auto_download:
                    tariff_rate = line._fetch_tariff_rate(search_code, country_code)
                else:
                    tariff_rate = None

                if tariff_rate is not None:
                    line.l10n_bg_tariff_rate = tariff_rate
                    line.l10n_bg_tariff_last_update = fields.Datetime.now()
                    _logger.info(f"Updated tariff rate for code {line.l10n_bg_tariff_code}: {tariff_rate * 100}%")
                else:
                    if not line.l10n_bg_tariff_rate:
                        default_rate = company.l10n_bg_default_tariff_rate
                        if default_rate > 1:
                            default_rate = default_rate / 100.0
                        line.l10n_bg_tariff_rate = default_rate

            except Exception as e:
                _logger.warning(f"Error looking up tariff rate for code {line.l10n_bg_tariff_code}: {e}")
                if not line.l10n_bg_tariff_rate:
                    default_rate = company.l10n_bg_default_tariff_rate
                    if default_rate > 1:
                        default_rate = default_rate / 100.0
                    line.l10n_bg_tariff_rate = default_rate

    def _inverse_l10n_bg_tariff_rate(self):
        """Позволява ръчно въвеждане на тарифна ставка"""
        for line in self:
            if line.l10n_bg_tariff_rate is not False:
                # Запазваме ръчно въведената стойност
                line.l10n_bg_tariff_rate_manual = line.l10n_bg_tariff_rate
                line.l10n_bg_tariff_rate_is_manual = True
                line.l10n_bg_tariff_last_update = fields.Datetime.now()

    def _fetch_tariff_rate(self, cn_code, country_code='CN'):
        """
        Търси тарифна ставка в ЕС ТАРИК системата чрез REST API

        Използва следните източници (по приоритет):
        1. UK Trade Tariff API (xi) - Northern Ireland използва EU TARIC данни
        2. API Store - неофициален агрегатор на EU Open Data
        3. Default rates - fallback
        """
        formatted_code = cn_code[:10].ljust(10, '0') if len(cn_code) <= 10 else cn_code[:10]

        # Метод 1: UK Trade Tariff API - най-надежден публичен източник за EU TARIC
        rate = self._fetch_from_uk_tariff_xi(formatted_code, country_code)
        if rate is not None:
            return rate

        # Метод 2: Опит с API Store (ако е конфигуриран)
        company = self.env.company
        if company.l10n_bg_taric_api_url and 'api.store' in company.l10n_bg_taric_api_url:
            rate = self._fetch_from_api_store(formatted_code, country_code)
            if rate is not None:
                return rate

        # Метод 3: Default rates
        return self._get_default_tariff_rate(country_code)

    def _fetch_from_uk_tariff_xi(self, cn_code, country_code='CN', max_retries=3):
        """
        Извлича данни от UK Trade Tariff API (Northern Ireland - XI)
        Този API използва EU TARIC данни за Северна Ирландия

        API Documentation: https://api.trade-tariff.service.gov.uk/
        """
        # Първо опитваме с пълния код
        _logger.info(f"UK Tariff (XI): Trying to fetch tariff for {cn_code}")

        result = self._try_fetch_uk_tariff_xi(cn_code, country_code, max_retries)
        if result is not None:
            _logger.info(f"✓ UK Tariff (XI): Found rate for {cn_code}")
            return result

        # Ако не сме намерили duty rate, но commodity съществува,
        # не опитваме с по-къси варианти (те са невалидни)
        _logger.info(f"UK Tariff (XI): No duty rate found for {cn_code}, using default")
        return None

    def _try_fetch_uk_tariff_xi(self, cn_code, country_code='CN', max_retries=3):
        """Вътрешен метод за опит с конкретен код"""
        for attempt in range(max_retries):
            try:
                # XI (Northern Ireland) следва EU TARIC правилата
                urls_to_try = [
                    f"https://www.trade-tariff.service.gov.uk/xi/api/v2/commodities/{cn_code}",
                    f"https://api.trade-tariff.service.gov.uk/xi/api/v2/commodities/{cn_code}",
                ]

                params = {'as_of': fields.Date.today().isoformat()}
                headers = {
                    'User-Agent': 'Odoo-BG-Tariff/2.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }

                response = None
                for url in urls_to_try:
                    _logger.info(f"UK Tariff (XI): Requesting {url}")
                    try:
                        response = requests.get(url, params=params, headers=headers, timeout=15)
                        _logger.info(f"UK Tariff (XI): Response status {response.status_code}")

                        if response.status_code == 200:
                            break
                        elif response.status_code == 404:
                            continue
                    except Exception as e:
                        _logger.debug(f"UK Tariff (XI): Error from {url}: {e}")
                        continue

                if not response or response.status_code != 200:
                    return None

                data = response.json()
                _logger.info(f"UK Tariff (XI): Successfully parsed JSON")

                # Извличаме описанието
                if 'data' in data and 'attributes' in data['data']:
                    description = data['data']['attributes'].get('description')
                    if description and not self.l10n_bg_tariff_description:
                        self.l10n_bg_tariff_description = description

                # Търсим мерки (measures)
                if 'included' not in data:
                    return None

                applicable_rates = []

                for item in data['included']:
                    if item.get('type') != 'measure':
                        continue

                    relationships = item.get('relationships', {})

                    # Извличаме measure_type
                    measure_type_data = relationships.get('measure_type', {}).get('data', {})
                    measure_type = measure_type_data.get('id') if isinstance(measure_type_data, dict) else None

                    # Извличаме geographical_area
                    geo_area_data = relationships.get('geographical_area', {}).get('data', {})
                    geo_area = geo_area_data.get('id') if isinstance(geo_area_data, dict) else None

                    # Проверяваме geographical_area
                    country_specific = False
                    if geo_area and geo_area == country_code:
                        country_specific = True
                    elif geo_area and geo_area != '1011' and geo_area != country_code:
                        continue

                    # Measure types
                    applicable_measure_types = ['103', '105', '142', '112', '695', '551', '552', '553', '554']

                    if measure_type and str(measure_type) in applicable_measure_types:
                        duty_expr_id = relationships.get('duty_expression', {}).get('data', {}).get('id')

                        # Намираме duty_expression
                        duty_expression = None
                        for included_item in data.get('included', []):
                            if (included_item.get('type') == 'duty_expression' and
                                included_item.get('id') == duty_expr_id):
                                duty_expression = included_item.get('attributes', {})
                                break

                        if duty_expression:
                            base = duty_expression.get('base', '')
                            formatted_base = duty_expression.get('formatted_base', '')

                            if base:
                                numbers = re.findall(r'\d+\.?\d*', str(base))
                                if numbers:
                                    rate = float(numbers[0])

                                    # КОНВЕРТИРАМЕ В DECIMAL ФОРМАТ (0.50 = 50%)
                                    if '%' in str(formatted_base) or '%' in str(base):
                                        rate_decimal = rate / 100.0
                                    elif rate > 100:
                                        rate_decimal = rate / 10000.0
                                    elif rate > 1:
                                        rate_decimal = rate / 100.0
                                    else:
                                        rate_decimal = rate

                                    # Приоритет
                                    priority = 0
                                    if country_specific:
                                        priority = 100
                                    elif measure_type in ['695', '551', '552', '553', '554']:
                                        priority = 50
                                    elif measure_type == '103':
                                        priority = 10
                                    else:
                                        priority = 5

                                    applicable_rates.append({
                                        'rate': rate_decimal,
                                        'type': measure_type,
                                        'priority': priority,
                                        'geo_area': geo_area,
                                        'country_specific': country_specific
                                    })

                                    _logger.info(
                                        f"UK Tariff (XI): Found {rate}% = {rate_decimal} decimal "
                                        f"(type {measure_type}, priority {priority})")

                # Избираме ставката с най-висок приоритет
                if applicable_rates:
                    applicable_rates.sort(key=lambda x: (-x['priority'], -x['rate']))
                    best_rate = applicable_rates[0]

                    _logger.info(
                        f"✓ UK Tariff (XI): Selected rate {best_rate['rate'] * 100}% "
                        f"(type {best_rate['type']}, country_specific: {best_rate['country_specific']})")

                    return best_rate['rate']

                return None

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None

            except requests.exceptions.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None

            except Exception as e:
                _logger.error(f"UK Tariff (XI) error: {e}", exc_info=True)
                return None

        return None

    def _fetch_from_api_store(self, cn_code, country_code='CN', max_retries=2):
        """Извлича данни от API Store"""
        try:
            company = self.env.company
            if not company.l10n_bg_taric_api_url:
                return None

            headers = {
                'User-Agent': 'Odoo-BG-Tariff/2.0',
                'Accept': 'application/json',
            }

            for attempt in range(max_retries):
                try:
                    params = {'code': cn_code, 'country': country_code}
                    response = requests.get(
                        company.l10n_bg_taric_api_url,
                        params=params,
                        headers=headers,
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()
                        rate = self._parse_api_store_response(data, cn_code)
                        if rate is not None:
                            return rate
                    elif response.status_code == 404:
                        return None

                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                except requests.exceptions.RequestException:
                    break

        except Exception as e:
            _logger.error(f"API Store error: {e}")

        return None

    def _parse_api_store_response(self, data, cn_code):
        """Парсва отговора от API Store"""
        try:
            if not data or not isinstance(data, dict):
                return None

            measures = []
            if 'measures' in data:
                measures = data['measures']
            elif 'data' in data:
                if isinstance(data['data'], list):
                    measures = data['data']
                elif isinstance(data['data'], dict):
                    if 'measures' in data['data']:
                        measures = data['data']['measures']
                    elif 'attributes' in data['data']:
                        measures = [data['data']]

            for measure in measures:
                if not isinstance(measure, dict):
                    continue

                desc = measure.get('description') or measure.get('goods_nomenclature_description')
                if desc and not self.l10n_bg_tariff_description:
                    self.l10n_bg_tariff_description = str(desc)

                duty_expr = measure.get('duty_expression') or measure.get('dutyExpression')
                if not duty_expr:
                    continue

                duty_amount = duty_expr.get('duty_amount') or duty_expr.get('dutyAmount')
                if duty_amount:
                    try:
                        rate = float(duty_amount)
                        measurement_unit = str(
                            duty_expr.get('measurement_unit', '') or duty_expr.get('measurementUnit', ''))
                        formatted_base = str(duty_expr.get('formatted_base', '') or duty_expr.get('formattedBase', ''))

                        # КОНВЕРТИРАМЕ В DECIMAL
                        if '%' in formatted_base or 'percent' in measurement_unit.lower():
                            return rate / 100.0
                        elif rate > 100:
                            return rate / 10000.0
                        elif rate > 1:
                            return rate / 100.0
                        else:
                            return rate

                    except (ValueError, TypeError):
                        continue

        except Exception as e:
            _logger.warning(f"Error parsing API Store: {e}")

        return None

    def _get_default_tariff_rate(self, country_code):
        """Връща стандартната тарифна ставка според страната на произход"""
        cached_rate = self._get_cached_taric_rate(self.l10n_bg_tariff_code, country_code)
        if cached_rate is not None:
            return cached_rate

        # ВСИЧКИ RATES В DECIMAL ФОРМАТ
        default_rates = {
            'CN': 0.065, 'IN': 0.045, 'US': 0.032, 'JP': 0.021, 'KR': 0.025,
            'TR': 0.018, 'TH': 0.030, 'VN': 0.042, 'MY': 0.035, 'ID': 0.040,
        }

        eu_countries = ['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
                        'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
                        'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']

        if country_code in eu_countries:
            return 0.0

        rate = default_rates.get(country_code, 0.065)
        _logger.info(f"Using default rate {rate * 100}% for country {country_code}")
        return rate

    def _get_cached_taric_rate(self, cn_code, country_code):
        """Извлича тарифна ставка от локалния кеш"""
        if not cn_code:
            return None

        TaricCache = self.env['l10n_bg.taric.cache']
        cache_record = TaricCache.search([
            ('cn_code', '=', cn_code),
            ('country_code', '=', country_code),
            ('valid_from', '<=', fields.Date.today()),
            ('valid_to', '>=', fields.Date.today()),
        ], limit=1)

        if cache_record:
            return cache_record.duty_rate

        return None

    def action_update_tariff_rate(self):
        """Ръчно обновяване на тарифната ставка"""
        updated_count = 0
        for line in self:
            if line.l10n_bg_tariff_code:
                line.l10n_bg_tariff_last_update = False
                line._compute_l10n_bg_tariff_rate()
                updated_count += 1

        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'success',
                'message': f'Обновени {updated_count} тарифни ставки от EU TARIC',
                'sticky': False,
            }
        )

    def action_sync_hs_codes(self):
        """Синхронизира HS кодовете с продуктите"""
        updated_products = 0
        products_updated = self.env['product.product']

        for line in self:
            if (line.product_id and line.l10n_bg_tariff_code
                and hasattr(line.product_id, 'hs_code')
                and not line.product_id.hs_code
                and line.product_id not in products_updated):
                try:
                    line.product_id.sudo().write({'hs_code': line.l10n_bg_tariff_code})
                    products_updated |= line.product_id
                    updated_products += 1
                except Exception as e:
                    _logger.warning(f"Error updating product HS code {line.product_id.name}: {e}")

        if updated_products > 0:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'message': f'Обновени HS кодове за {updated_products} продукта',
                    'sticky': False,
                }
            )
        else:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'message': 'There are no products to update',
                    'sticky': False,
                }
            )
