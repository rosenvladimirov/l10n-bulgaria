
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
        help="Ръчно въведен тарифен код"
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
        help="Ръчно въведена тарифна ставка"
    )

    l10n_bg_tariff_description = fields.Text(
        string='Tariff Description',
        help="Описание от ТАРИК системата"
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
                normalized = self._normalize_tariff_code(line.product_id.hs_code)
                if normalized:
                    tariff_code = normalized

            # 3. Опит за извличане от intrastat (чрез override метод)
            if not tariff_code and line.product_id:
                intrastat_code = line._get_tariff_code_from_intrastat(line.product_id)
                if intrastat_code:
                    normalized = self._normalize_tariff_code(intrastat_code)
                    if normalized:
                        tariff_code = normalized.ljust(10, '0')

            # 4. Търсим в описанието на реда
            if not tariff_code and line.name:
                tariff_code = self._extract_code_from_text(line.name)

            # 5. Fallback към категорията на продукта
            if not tariff_code and line.product_id and line.product_id.categ_id:
                tariff_code = self._get_category_tariff_code(line.product_id.categ_id)

            line.l10n_bg_tariff_code = tariff_code

    def _inverse_l10n_bg_tariff_code(self):
        """Позволява ръчно задаване на тарифен код"""
        for line in self:
            if line.l10n_bg_tariff_code:
                normalized = self._normalize_tariff_code(line.l10n_bg_tariff_code)
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
                        _logger.info(f"Обновен HS код на продукт {line.product_id.name}: {normalized}")
                    except Exception as e:
                        _logger.warning(f"Не може да се обнови HS кода на продукта: {e}")

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

            # Защита срещу изтрити записи
            if line.product_id and isinstance(line.product_id.id, int) and not line.product_id.exists():
                _logger.warning(f"Продуктът за ред {line.id} не съществува")
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
                    line.l10n_bg_tariff_rate = company.l10n_bg_default_tariff_rate
                continue

            try:
                search_code = line.l10n_bg_tariff_code[:8] if len(
                    line.l10n_bg_tariff_code) >= 8 else line.l10n_bg_tariff_code.ljust(8, '0')

                # Използваме country_of_origin от продукта
                country_code = 'CN'  # по подразбиране
                if line.product_id and hasattr(line.product_id,
                                               'country_of_origin') and line.product_id.country_of_origin:
                    country_code = line.product_id.country_of_origin.code

                tariff_rate = self._fetch_tariff_rate(search_code, country_code)

                if tariff_rate is not None:
                    line.l10n_bg_tariff_rate = tariff_rate
                    line.l10n_bg_tariff_last_update = fields.Datetime.now()
                    _logger.info(f"Обновена тарифна ставка за код {line.l10n_bg_tariff_code}: {tariff_rate}%")
                else:
                    if not line.l10n_bg_tariff_rate:
                        line.l10n_bg_tariff_rate = company.l10n_bg_default_tariff_rate

            except Exception as e:
                _logger.warning(f"Грешка при търсене на тарифна ставка за код {line.l10n_bg_tariff_code}: {e}")
                if not line.l10n_bg_tariff_rate:
                    line.l10n_bg_tariff_rate = company.l10n_bg_default_tariff_rate

    def _inverse_l10n_bg_tariff_rate(self):
        """Позволява ръчно въвеждане на тарифна ставка"""
        for line in self:
            if line.l10n_bg_tariff_rate is not False:
                # Запазваме ръчно въведената стойност
                line.l10n_bg_tariff_rate_manual = line.l10n_bg_tariff_rate
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
                # Опитваме различни API endpoints
                urls_to_try = [
                    f"https://www.trade-tariff.service.gov.uk/xi/api/v2/commodities/{cn_code}",
                    f"https://api.trade-tariff.service.gov.uk/xi/api/v2/commodities/{cn_code}",
                ]

                params = {
                    'as_of': fields.Date.today().isoformat(),
                }

                headers = {
                    'User-Agent': 'Odoo-BG-Tariff/2.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }

                response = None
                for url in urls_to_try:
                    _logger.info(f"UK Tariff (XI): Requesting {url} with params {params}")
                    try:
                        response = requests.get(url, params=params, headers=headers, timeout=15)
                        _logger.info(f"UK Tariff (XI): Response status {response.status_code} for {cn_code} from {url}")

                        if response.status_code == 200:
                            break
                        elif response.status_code == 404:
                            _logger.debug(f"UK Tariff (XI): 404 from {url}, trying next endpoint")
                            continue
                    except Exception as e:
                        _logger.debug(f"UK Tariff (XI): Error from {url}: {e}")
                        continue

                if not response or response.status_code != 200:
                    if response:
                        _logger.debug(f"UK Tariff (XI): Final status {response.status_code} for {cn_code}")
                        if response.status_code in [403, 404]:
                            _logger.debug(f"UK Tariff (XI): Response text: {response.text[:500]}")
                    return None

                try:
                    data = response.json()
                    _logger.info(f"UK Tariff (XI): Successfully parsed JSON response for {cn_code}")
                except ValueError as e:
                    _logger.warning(f"UK Tariff (XI): Invalid JSON response for {cn_code}: {e}")
                    return None

                # Извличаме описанието
                if 'data' in data and 'attributes' in data['data']:
                    description = data['data']['attributes'].get('description')
                    if description:
                        _logger.info(f"UK Tariff (XI): Found description for {cn_code}: {description[:100]}")
                        if not self.l10n_bg_tariff_description:
                            self.l10n_bg_tariff_description = description

                # Търсим мерки (measures)
                if 'included' in data:
                    measures_count = sum(1 for item in data['included'] if item.get('type') == 'measure')
                    _logger.info(f"UK Tariff (XI): Found {measures_count} measures in response for {cn_code}")

                    applicable_rates = []

                    for item in data['included']:
                        if item.get('type') != 'measure':
                            continue

                        attrs = item.get('attributes', {})
                        relationships = item.get('relationships', {})

                        # Извличаме measure_type от relationships
                        measure_type_data = relationships.get('measure_type', {}).get('data', {})
                        measure_type = measure_type_data.get('id') if isinstance(measure_type_data, dict) else None

                        # Извличаме geographical_area от relationships
                        geo_area_data = relationships.get('geographical_area', {}).get('data', {})
                        geo_area = geo_area_data.get('id') if isinstance(geo_area_data, dict) else None

                        _logger.debug(f"UK Tariff (XI): Measure - type: {measure_type}, geo: {geo_area}")

                        # Проверяваме за географска област (страна на произход)
                        country_specific = False
                        if geo_area and geo_area == country_code:
                            country_specific = True
                            _logger.info(f"UK Tariff (XI): Found country-specific measure for {country_code}")
                        elif geo_area and geo_area != '1011' and geo_area != country_code:
                            _logger.debug(f"UK Tariff (XI): Skipping measure - geo_area {geo_area} doesn't match {country_code}")
                            continue

                        # Разширен списък от measure types
                        applicable_measure_types = ['103', '105', '142', '112', '695', '551', '552', '553', '554']

                        if measure_type and str(measure_type) in applicable_measure_types:
                            _logger.info(f"UK Tariff (XI): Found applicable measure type {measure_type} for {cn_code}")

                            # Duty expression трябва да се търси в included секцията
                            duty_expr_id = relationships.get('duty_expression', {}).get('data', {}).get('id')
                            _logger.debug(f"UK Tariff (XI): Duty expression ID: {duty_expr_id}")

                            # Намираме duty_expression в included
                            duty_expression = None
                            for included_item in data.get('included', []):
                                if (included_item.get('type') == 'duty_expression' and
                                    included_item.get('id') == duty_expr_id):
                                    duty_expression = included_item.get('attributes', {})
                                    break

                            if duty_expression:
                                base = duty_expression.get('base', '')
                                formatted_base = duty_expression.get('formatted_base', '')

                                _logger.info(f"UK Tariff (XI): Duty base: '{base}', formatted: '{formatted_base}'")

                                if base:
                                    # Извличаме числовата стойност
                                    numbers = re.findall(r'\d+\.?\d*', str(base))
                                    if numbers:

                                        rate = float(numbers[0])
                                        _logger.info(f"UK Tariff (XI): Extracted rate value: {rate}")

                                        # КОНВЕРТИРАМЕ ВСИЧКИ СТАВКИ В DECIMAL ФОРМАТ (0.50 = 50%)
                                        # Проверяваме дали е процент
                                        if '%' in str(formatted_base) or '%' in str(base):
                                            # rate е вече в проценти (50), конвертираме в decimal
                                            rate_decimal = rate / 100.0
                                            _logger.info(f"UK Tariff (XI): Converted {rate}% to decimal {rate_decimal}")
                                        elif rate > 100:
                                            # Конвертираме от basis points (5000 -> 50 -> 0.50)
                                            rate_decimal = rate / 10000.0
                                            _logger.info(
                                                f"UK Tariff (XI): Converted from basis points: {rate} -> {rate_decimal}")
                                        elif rate > 1:
                                            # Вероятно е в проценти без символ (50 -> 0.50)
                                            rate_decimal = rate / 100.0
                                            _logger.info(
                                                f"UK Tariff (XI): Assumed percentage, converted {rate} -> {rate_decimal}")
                                        else:
                                            # Вече е в decimal формат (0.50)
                                            rate_decimal = rate
                                            _logger.info(f"UK Tariff (XI): Already in decimal format: {rate_decimal}")

                                        # Приоритет: country-specific > additional duties > standard duties
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
                                            'rate': rate_decimal,  # Съхраняваме в decimal формат
                                            'type': measure_type,
                                            'priority': priority,
                                            'geo_area': geo_area,
                                            'country_specific': country_specific
                                        })

                                        _logger.info(
                                            f"UK Tariff (XI): Found rate {rate}% (stored as {rate_decimal}) for {cn_code} "
                                            f"(type {measure_type}, priority {priority}, geo {geo_area})")

                    # Избираме ставката с най-висок приоритет
                    if applicable_rates:
                        applicable_rates.sort(key=lambda x: (-x['priority'], -x['rate']))
                        best_rate = applicable_rates[0]

                        _logger.info(
                            f"✓ UK Tariff (XI): Selected rate {best_rate['rate']}% for {cn_code} "
                            f"(type {best_rate['type']}, geo {best_rate['geo_area']}, "
                            f"country_specific: {best_rate['country_specific']})")

                        if len(applicable_rates) > 1:
                            other_rates = [f"{r['rate']}% (type {r['type']})" for r in applicable_rates[1:]]
                            _logger.info(f"UK Tariff (XI): Other available rates: {', '.join(other_rates)}")

                        return best_rate['rate']

                    # Ако не сме намерили нищо, изброяваме всички measure types
                    all_measure_types = set()
                    all_geo_areas = set()
                    for item in data['included']:
                        if item.get('type') == 'measure':
                            rels = item.get('relationships', {})
                            mt_data = rels.get('measure_type', {}).get('data', {})
                            ga_data = rels.get('geographical_area', {}).get('data', {})

                            mt = mt_data.get('id') if isinstance(mt_data, dict) else 'unknown'
                            ga = ga_data.get('id') if isinstance(ga_data, dict) else 'unknown'

                            all_measure_types.add(str(mt))
                            all_geo_areas.add(str(ga))

                    _logger.info(f"UK Tariff (XI): Available measure types for {cn_code}: {sorted(all_measure_types)}")
                    _logger.info(f"UK Tariff (XI): Available geo areas for {cn_code}: {sorted(all_geo_areas)}")

                else:
                    _logger.info(f"UK Tariff (XI): No 'included' section in response for {cn_code}")

                return None

            except requests.exceptions.Timeout:
                _logger.warning(f"UK Tariff (XI) timeout for {cn_code} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None

            except requests.exceptions.RequestException as e:
                _logger.info(f"UK Tariff (XI) request error for {cn_code}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None

            except Exception as e:
                _logger.error(f"UK Tariff (XI) unexpected error for {cn_code}: {e}")
                _logger.error(f"UK Tariff (XI) full traceback:", exc_info=True)
                return None

        return None

    def _fetch_from_api_store(self, cn_code, country_code='CN', max_retries=2):
        """
        Извлича данни от API Store - неофициален агрегатор на EU Open Data
        API Store е третостранна услуга: https://api.store/

        Забележка: Този метод изисква конфигуриран URL в настройките
        """
        try:
            company = self.env.company
            base_url = company.l10n_bg_taric_api_url

            if not base_url:
                return None

            headers = {
                'User-Agent': 'Odoo-BG-Tariff/2.0',
                'Accept': 'application/json',
            }

            for attempt in range(max_retries):
                try:
                    params = {
                        'code': cn_code,
                        'country': country_code,
                    }

                    response = requests.get(
                        base_url,
                        params=params,
                        headers=headers,
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()
                        rate = self._parse_api_store_response(data, cn_code)
                        if rate is not None:
                            _logger.info(f"✓ API Store: Found rate {rate}% for {cn_code}")
                            return rate

                    elif response.status_code == 404:
                        _logger.info(f"API Store: No data found for {cn_code}")
                        return None

                except requests.exceptions.Timeout:
                    _logger.warning(f"API Store timeout (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue

                except requests.exceptions.RequestException as e:
                    _logger.warning(f"API Store request error: {e}")
                    break

        except Exception as e:
            _logger.error(f"API Store unexpected error: {e}")

        return None

    def _parse_api_store_response(self, data, cn_code):
        """Парсва отговора от API Store и извлича duty rate"""
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

            if not measures:
                return None

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

                        # КОНВЕРТИРАМЕ В DECIMAL ФОРМАТ
                        if '%' in formatted_base or 'percent' in measurement_unit.lower():
                            # rate е в проценти, конвертираме в decimal
                            return rate / 100.0
                        elif rate > 100:
                            # Basis points
                            return rate / 10000.0
                        elif rate > 1:
                            # Вероятно проценти
                            return rate / 100.0
                        else:
                            # Вече decimal
                            return rate

                    except (ValueError, TypeError):
                        continue

        except Exception as e:
            _logger.warning(f"Error parsing API Store response: {e}")

        return None

    def _get_default_tariff_rate(self, country_code):
        """Връща стандартната тарифна ставка според страната на произход"""
        cached_rate = self._get_cached_taric_rate(self.l10n_bg_tariff_code, country_code)
        if cached_rate is not None:
            _logger.info(f"Using cached TARIC rate {cached_rate} for {self.l10n_bg_tariff_code}")
            return cached_rate

        # ВСИЧКИ DEFAULT RATES В DECIMAL ФОРМАТ
        default_rates = {
            'CN': 0.065,  # 6.5%
            'IN': 0.045,  # 4.5%
            'US': 0.032,  # 3.2%
            'JP': 0.021,  # 2.1%
            'KR': 0.025,  # 2.5%
            'TR': 0.018,  # 1.8%
            'TH': 0.030,  # 3.0%
            'VN': 0.042,  # 4.2%
            'MY': 0.035,  # 3.5%
            'ID': 0.040,  # 4.0%
        }

        eu_countries = ['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
                        'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
                        'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']

        if country_code in eu_countries:
            return 0.0

        # Company default също трябва да е в decimal
        rate = default_rates.get(country_code, self.env.company.l10n_bg_default_tariff_rate / 100.0)
        _logger.info(f"Using default rate {rate} ({rate * 100}%) for country {country_code}")
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
                    'message': 'Няма продукти за обновяване',
                    'sticky': False,
                }
            )
