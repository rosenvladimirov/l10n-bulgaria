# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
import requests
import logging
import re

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_bg_price_unit = fields.Monetary(
        string='Unit price currency (balance)',
        compute='_compute_l10n_bg_price_unit', store=True, readonly=False,
        currency_field='company_currency_id',
        tracking=True,
    )

    # Митнически данни
    l10n_bg_customs_value = fields.Monetary(
        string='Customs Value',
        currency_field='currency_id',
        help="Customs value of the goods"
    )

    l10n_bg_weight_gross = fields.Float(
        string='Gross Weight (kg)',
        help="Бруто тегло в килограми"
    )

    l10n_bg_weight_net = fields.Float(
        string='Net Weight (kg)',
        help="Net weight in kilograms"
    )

    l10n_bg_customs_procedure_id = fields.Many2one(
        'l10n.bg.customs.nomenclature',
        string='Customs Procedure',
        domain=[('type', '=', 'procedure')],
        help="Митнически режим"
    )

    l10n_bg_is_customs_expense = fields.Boolean(
        string='Is Customs Expense',
        help="Notes if this is a customs fee/expense"
    )

    # Използваме съществуващото поле за страна на произход вместо ново
    # l10n_bg_country_origin_id - ПРЕМАХНАТО (използваме product_id.country_of_origin)

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
        help="Tariff rate from the EU Tarik System"
    )

    l10n_bg_tariff_description = fields.Text(
        string='Tariff Description',
        help="Описание от ТАРИК системата"
    )

    l10n_bg_tariff_last_update = fields.Datetime(
        string='Tariff Last Update',
        help="Last tariff rate update"
    )

    @api.depends('balance')
    def _compute_l10n_bg_price_unit(self):
        for line in self:
            quantity = line.quantity == 0 and 1 or line.quantity
            line.l10n_bg_price_unit = line.balance / quantity

    def _get_tariff_code_from_intrastat(self, product):
        """Метод за извличане на тарифен код от intrastat система

        Този метод е предназначен за override в други модули
        които имплементират интеграция с intrastat системата.
        """
        # Може да се override в други модули
        pass

    @api.depends('product_id', 'product_id.default_code', 'product_id.hs_code',
                 'name', 'l10n_bg_tariff_code_manual')
    def _compute_l10n_bg_tariff_code(self):
        """Извлича тарифния код с backward compatibility за HS и Intrastat"""
        for line in self:
            tariff_code = False

            # 1. Първо проверяваме ръчно въведения код
            if line.l10n_bg_tariff_code_manual:
                tariff_code = line._normalize_tariff_code(line.l10n_bg_tariff_code_manual)

            # 2. HS Code от stock_delivery модула (приоритет)
            if not tariff_code and line.product_id and line.product_id.hs_code:
                normalized = self._normalize_tariff_code(line.product_id.hs_code)
                if normalized:
                    tariff_code = normalized

            # 3. Опит за извличане от intrastat (чрез override метод)
            if not tariff_code and line.product_id:
                intrastat_code = line._get_tariff_code_from_intrastat(line.product_id)
                if intrastat_code:
                    normalized = self._normalize_tariff_code(intrastat_code)
                    if normalized:
                        tariff_code = normalized.ljust(10, '0')  # Допълваме до 10 цифри

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
                if (line.product_id and not line.product_id.hs_code and
                    normalized and len(normalized) >= 6):
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
            return digits_only + "00"  # Стандартен CN код
        elif len(digits_only) == 8:  # CN код
            return digits_only
        elif len(digits_only) >= 10:  # Пълен код с подкатегории
            return digits_only[:10]  # Вземаме първите 10 цифри
        else:
            # 7 или 9 цифри - допълваме до най-близкия стандарт
            if len(digits_only) == 7:
                return digits_only + "0"  # Правим го 8 цифри (CN)
            else:  # 9 цифри
                return digits_only + "0"  # Правим го 10 цифри

        return digits_only

    def _extract_code_from_text(self, text):
        """Извлича тарифен/HS/CN код от текст с различни формати"""
        if not text:
            return False

        patterns = [
            r'CN:?\s*(\d{8,10})',  # CN: 85333900
            r'HS:?\s*(\d{6,10})',  # HS: 853339
            r'code:?\s*(\d{6,10})',  # code: 853339
            r'intrastat:?\s*(\d{8})',  # intrastat: 85333900
            r'tariff:?\s*(\d{6,10})',  # tariff: 853339
            r'commodity:?\s*(\d{6,10})',  # commodity: 853339
            r'(\d{8,10})(?=\s|$|[^\d])',  # самостоятелни 8-10 цифри
            r'(\d{6})(?=\s|$|[^\d])',  # самостоятелни 6 цифри (HS)
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

    @api.depends('l10n_bg_tariff_code', 'product_id.country_of_origin')
    def _compute_l10n_bg_tariff_rate(self):
        """Автоматично търси тарифната ставка в ЕС ТАРИК - използва product_id.country_of_origin"""
        for line in self:
            if not line.l10n_bg_tariff_code:
                line.l10n_bg_tariff_rate = 0.0
                continue

            # Проверяваме дали имаме кеширана стойност
            company = line.company_id or self.env.company
            cache_duration = getattr(company, 'l10n_bg_taric_cache_duration', 24) * 3600

            if (line.l10n_bg_tariff_last_update and
                line.l10n_bg_tariff_rate is not False and
                (fields.Datetime.now() - line.l10n_bg_tariff_last_update).total_seconds() < cache_duration):
                continue

            if not getattr(company, 'l10n_bg_taric_api_enabled', True):
                if not line.l10n_bg_tariff_rate:
                    line.l10n_bg_tariff_rate = getattr(company, 'l10n_bg_default_tariff_rate', 5.0)
                continue

            try:
                search_code = line.l10n_bg_tariff_code[:8] if len(
                    line.l10n_bg_tariff_code) >= 8 else line.l10n_bg_tariff_code.ljust(8, '0')

                # Използваме country_of_origin от продукта вместо отделно поле
                country_code = 'CN'  # по подразбиране
                if line.product_id and line.product_id.country_of_origin:
                    country_code = line.product_id.country_of_origin.code

                tariff_rate = self._fetch_tariff_rate(search_code, country_code)

                if tariff_rate is not None:
                    line.l10n_bg_tariff_rate = tariff_rate
                    line.l10n_bg_tariff_last_update = fields.Datetime.now()
                    _logger.info(f"Обновена тарифна ставка за код {line.l10n_bg_tariff_code}: {tariff_rate}%")
                else:
                    if not line.l10n_bg_tariff_rate:
                        line.l10n_bg_tariff_rate = getattr(company, 'l10n_bg_default_tariff_rate', 5.0)

            except Exception as e:
                _logger.warning(f"Грешка при търсене на тарифна ставка за код {line.l10n_bg_tariff_code}: {e}")
                if not line.l10n_bg_tariff_rate:
                    line.l10n_bg_tariff_rate = getattr(company, 'l10n_bg_default_tariff_rate', 5.0)

    def _inverse_l10n_bg_tariff_rate(self):
        """Позволява ръчно въвеждане на тарифна ставка"""
        for line in self:
            if line.l10n_bg_tariff_rate is not False:
                line.l10n_bg_tariff_last_update = fields.Datetime.now()

    def _fetch_tariff_rate(self, cn_code, country_code='CN'):
        """Търси тарифна ставка в ЕС ТАРИК системата"""
        company = self.env.company
        taric_api_url = getattr(company, 'l10n_bg_taric_api_url',
                                None) or 'https://ec.europa.eu/taxation_customs/dds2/taric/api/v1'

        if not cn_code or len(cn_code) < 6:
            return None

        formatted_code = cn_code[:8].ljust(8, '0')

        try:
            url = f"{taric_api_url}/measures"
            params = {
                'goods_nomenclature_item_id': formatted_code,
                'geographical_area_id': country_code,
                'at_time': fields.Date.today().strftime('%Y-%m-%d'),
                'measure_type': '103',  # Third country duty
                'lang': 'en'  # Задаваме език на английски
            }

            headers = {
                'User-Agent': 'Odoo-BG-Customs/1.0',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9'  # Допълнително указване на предпочитан език
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'data' in data and data['data']:
                    for measure in data['data']:
                        if 'duty_expression' in measure:
                            duty_expression = measure['duty_expression']
                            if 'duty_amount' in duty_expression:
                                rate = float(duty_expression['duty_amount'])

                                # Извличаме описанието на английски
                                if 'goods_nomenclature' in measure:
                                    description = measure['goods_nomenclature'].get('description', '')
                                    # Ако има описания на различни езици, вземаме английското
                                    if isinstance(description, dict):
                                        description = description.get('en', description.get('EN', str(description)))
                                    self.l10n_bg_tariff_description = description

                                return rate

                return self._get_default_tariff_rate(country_code)

            elif response.status_code == 404:
                return self._get_default_tariff_rate(country_code)
            else:
                _logger.warning(f"ТАРИК API грешка {response.status_code}: {response.text}")
                return None

        except requests.exceptions.Timeout:
            _logger.warning(f"Timeout при заявка към ТАРИК API за код {formatted_code}")
            return None
        except requests.exceptions.RequestException as e:
            _logger.warning(f"Мрежова грешка при заявка към ТАРИК API: {e}")
            return None
        except ValueError as e:
            _logger.warning(f"Грешка при парсиране на ТАРИК отговор: {e}")
            return None

    def _get_default_tariff_rate(self, country_code):
        """Връща стандартната тарифна ставка според страната на произход"""
        default_rates = {
            'CN': 6.5, 'IN': 4.5, 'US': 3.2, 'JP': 2.1, 'KR': 2.5,
            'TR': 1.8, 'TH': 3.0, 'VN': 4.2, 'MY': 3.5, 'ID': 4.0,
        }

        eu_countries = ['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
                        'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
                        'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']

        if country_code in eu_countries:
            return 0.0

        return default_rates.get(country_code, getattr(self.env.company, 'l10n_bg_default_tariff_rate', 5.0))

    @api.onchange('product_id')
    def _onchange_product_id_tariff(self):
        """Обновява тарифната информация при смяна на продукта"""
        if self.product_id:
            self._compute_l10n_bg_tariff_code()
            self._compute_l10n_bg_tariff_rate()

    def action_update_tariff_rate(self):
        """Ръчно обновяване на тарифната ставка"""
        updated_count = 0
        for line in self:
            if line.l10n_bg_tariff_code:
                line.l10n_bg_tariff_last_update = False
                line._compute_l10n_bg_tariff_rate()
                updated_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Updated {updated_count} tariff rates',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_hs_codes(self):
        """Синхронизира HS кодовете с продуктите"""
        updated_products = 0
        for line in self:
            if (line.product_id and line.l10n_bg_tariff_code and
                not line.product_id.hs_code):
                try:
                    line.product_id.sudo().write({'hs_code': line.l10n_bg_tariff_code})
                    updated_products += 1
                except Exception as e:
                    _logger.warning(f"HS code update error: {e}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Updated HS codes for {updated_products} products',
                'type': 'success',
                'sticky': False,
            }
        }
