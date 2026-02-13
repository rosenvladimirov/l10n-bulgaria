
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
from datetime import datetime

from odoo import models, fields, api
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
        help="Tariff rate (offline: cached or default)"
    )

    l10n_bg_tariff_rate_manual = fields.Float(
        string='Manual Tariff Rate (%)',
        help="Manually entered tariff rate"
    )

    l10n_bg_tariff_description = fields.Text(
        string='Tariff Description',
        help="Tariff description (offline)"
    )

    l10n_bg_tariff_last_update = fields.Datetime(
        string='Tariff Last Update',
        help="Last tariff rate update"
    )

    def _get_tariff_code_from_intrastat(self, product):
        """Extract tariff code from intrastat (override in other modules)."""
        return False

    @api.depends('product_id', 'name', 'l10n_bg_tariff_code_manual')
    def _compute_l10n_bg_tariff_code(self):
        """Extract tariff code with HS/Intrastat compatibility."""
        for line in self:
            tariff_code = False

            # Skip if product is missing or invalid
            if line.product_id:
                # Проверка за реален ID (не NewId) и съществуване
                if isinstance(line.product_id.id, int) and not line.product_id.exists():
                    _logger.warning(f"Product for line {line.id} does not exist")
                    line.l10n_bg_tariff_code = False
                    continue

            # 1. Manual code first
            if line.l10n_bg_tariff_code_manual:
                tariff_code = line._normalize_tariff_code(line.l10n_bg_tariff_code_manual)

            # 2. HS code from stock_delivery (priority)
            if not tariff_code and line.product_id and hasattr(line.product_id, 'hs_code') and line.product_id.hs_code:
                normalized = self._normalize_tariff_code(line.product_id.hs_code)
                if normalized:
                    tariff_code = normalized

            # 3. Try intrastat (via override)
            if not tariff_code and line.product_id:
                intrastat_code = line._get_tariff_code_from_intrastat(line.product_id)
                if intrastat_code:
                    normalized = self._normalize_tariff_code(intrastat_code)
                    if normalized:
                        tariff_code = normalized.ljust(10, '0')

            # 4. Search in line description
            if not tariff_code and line.name:
                tariff_code = self._extract_code_from_text(line.name)

            # 5. Fallback to product category
            if not tariff_code and line.product_id and line.product_id.categ_id:
                tariff_code = self._get_category_tariff_code(line.product_id.categ_id)

            line.l10n_bg_tariff_code = tariff_code

    def _inverse_l10n_bg_tariff_code(self):
        """Allow manual tariff code input."""
        for line in self:
            if line.l10n_bg_tariff_code:
                normalized = self._normalize_tariff_code(line.l10n_bg_tariff_code)
                line.l10n_bg_tariff_code_manual = normalized

                # If the product has no HS code, try to update it
                if (line.product_id
                    and isinstance(line.product_id.id, int)
                    and line.product_id.exists()
                    and hasattr(line.product_id, 'hs_code')
                    and not line.product_id.hs_code
                    and normalized and len(normalized) >= 6):
                    try:
                        line.product_id.sudo().write({'hs_code': normalized})
                        _logger.info(f"Updated HS code for product {line.product_id.name}: {normalized}")
                    except Exception as e:
                        _logger.warning(f"Unable to update product HS code: {e}")

    def _normalize_tariff_code(self, code_input):
        """Normalize tariff code from different formats."""
        if not code_input:
            return False

        # Keep digits only
        digits_only = "".join(filter(str.isdigit, str(code_input).upper()))

        if not digits_only:
            return False

        # Validate length
        if len(digits_only) < 6:  # Minimum for HS code
            return False
        elif len(digits_only) == 6:  # HS code -> pad to CN
            return digits_only + "00"
        elif len(digits_only) == 8:  # CN code
            return digits_only
        elif len(digits_only) >= 10:  # Full code with subcategories
            return digits_only[:10]
        else:
            # 7 or 9 digits -> pad to nearest standard
            if len(digits_only) == 7:
                return digits_only + "0"
            else:  # 9 digits
                return digits_only + "0"

        return digits_only

    def _extract_code_from_text(self, text):
        """Extract tariff/HS/CN code from text in various formats."""
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
        """Extract tariff code from product category."""
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
        """Compute tariff rate offline (cached or default)."""
        for line in self:
            # Manual rate has priority
            if line.l10n_bg_tariff_rate_manual:
                line.l10n_bg_tariff_rate = line.l10n_bg_tariff_rate_manual
                continue

            # Guard against deleted records
            if line.product_id and isinstance(line.product_id.id, int) and not line.product_id.exists():
                _logger.warning(f"Product for line {line.id} does not exist")
                line.l10n_bg_tariff_rate = 0.0
                continue

            if not line.l10n_bg_tariff_code:
                line.l10n_bg_tariff_rate = 0.0
                continue

            # Use cached value if still valid
            company = line.company_id or self.env.company
            cache_duration = company.l10n_bg_taric_cache_duration * 3600

            if (line.l10n_bg_tariff_last_update and
                line.l10n_bg_tariff_rate is not False and
                (fields.Datetime.now() - line.l10n_bg_tariff_last_update).total_seconds() < cache_duration):
                continue

            search_code = line.l10n_bg_tariff_code[:8] if len(
                line.l10n_bg_tariff_code) >= 8 else line.l10n_bg_tariff_code.ljust(8, '0')

            country_code = 'CN'
            if line.product_id and hasattr(line.product_id, 'country_of_origin') and line.product_id.country_of_origin:
                country_code = line.product_id.country_of_origin.code

            tariff_rate = self._fetch_tariff_rate(search_code, country_code)
            if tariff_rate is not None:
                line.l10n_bg_tariff_rate = tariff_rate
                line.l10n_bg_tariff_last_update = fields.Datetime.now()
            else:
                default_rate = company.l10n_bg_default_tariff_rate
                if default_rate > 1:
                    default_rate = default_rate / 100.0
                line.l10n_bg_tariff_rate = default_rate

    def _inverse_l10n_bg_tariff_rate(self):
        """Allow manual tariff rate input."""
        for line in self:
            if line.l10n_bg_tariff_rate is not False:
                # Запазваме ръчно въведената стойност
                line.l10n_bg_tariff_rate_manual = line.l10n_bg_tariff_rate
                line.l10n_bg_tariff_last_update = fields.Datetime.now()

    def _fetch_tariff_rate(self, cn_code, country_code='CN'):
        """Offline tariff rate lookup using local cache and defaults only."""
        formatted_code = cn_code[:10].ljust(10, '0') if len(cn_code) <= 10 else cn_code[:10]

        cached_rate = self._get_cached_taric_rate(formatted_code, country_code)
        if cached_rate is not None:
            return cached_rate

        return self._get_default_tariff_rate(country_code)

    def _fetch_from_uk_tariff_xi(self, cn_code, country_code='CN', max_retries=3):
        """
        Deprecated: online TARIC lookup is disabled.
        """
        return None

    def _try_fetch_uk_tariff_xi(self, cn_code, country_code='CN', max_retries=3):
        """Deprecated: online TARIC lookup is disabled."""
        return None

    def _fetch_from_api_store(self, cn_code, country_code='CN', max_retries=2):
        """Deprecated: online TARIC lookup is disabled."""
        return None

    def _parse_api_store_response(self, data, cn_code):
        """Parse API Store response (unused)."""
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
        """Return default tariff rate for country of origin."""
        cached_rate = self._get_cached_taric_rate(self.l10n_bg_tariff_code, country_code)
        if cached_rate is not None:
            return cached_rate

        # All rates are in decimal format
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
        """Get tariff rate from local cache."""
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
        """Manually recompute tariff rate (offline)."""
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
                'message': f'Recomputed {updated_count} tariff rates (offline)',
                'sticky': False,
            }
        )

    def action_sync_hs_codes(self):
        """Sync HS codes with products."""
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
                    'message': f'Updated HS codes for {updated_products} products',
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
