from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Полето hs_code вече съществува в stock_delivery модула
    # Добавяме само помощна информация

    taric_code = fields.Char(
        string='TARIC Code',
        help='TARIC код на продукта (синхронизиран с HS Code)'
    )

    l10n_bg_tariff_rate = fields.Float(
        string='Default Tariff Rate (%)',
        help='Cached tariff rate for this product',
        compute='_compute_l10n_bg_tariff_rate',
        inverse='_inverse_l10n_bg_tariff_rate',
        store=True
    )

    l10n_bg_tariff_rate_manual = fields.Float(
        string='Manual Tariff Rate (%)',
        help='Ръчно въведена тарифна ставка (приоритет над автоматичната)'
    )

    l10n_bg_tariff_last_update = fields.Datetime(
        string='Tariff Rate Last Update',
        help='When was the tariff rate last updated'
    )

    l10n_bg_tariff_description = fields.Text(
        string='Tariff Description',
        help='Description of the tariff rate for this product'
    )

    @api.onchange('hs_code')
    def _onchange_hs_code(self):
        """Синхронизира hs_code към taric_code"""
        if self.hs_code and self.hs_code != self.taric_code:
            self.taric_code = self.hs_code

    @api.onchange('taric_code')
    def _onchange_taric_code(self):
        """Синхронизира taric_code към hs_code"""
        if self.taric_code and self.taric_code != self.hs_code:
            self.hs_code = self.taric_code

    @api.depends('hs_code', 'taric_code', 'country_of_origin', 'l10n_bg_tariff_rate_manual')
    def _compute_l10n_bg_tariff_rate(self):
        """Изчислява тарифната ставка за продукта"""
        MoveLine = self.env['account.move.line']
        for product in self:
            _logger.info(f"Computing tariff rate for product {product.id} ({product.name})")

            # Ако има ръчно въведена ставка, използваме нея
            if product.l10n_bg_tariff_rate_manual:
                _logger.info(f"Using manual rate {product.l10n_bg_tariff_rate_manual} for product {product.id}")
                product.l10n_bg_tariff_rate = product.l10n_bg_tariff_rate_manual
                continue

            # Използваме taric_code или hs_code (приоритет на taric_code)
            code = product.taric_code or product.hs_code
            if not code:
                _logger.info(f"No TARIC/HS code for product {product.id}")
                product.l10n_bg_tariff_rate = 0.0
                continue

            # Използваме логиката от account.move.line
            country_code = product.country_of_origin.code if product.country_of_origin else 'CN'
            _logger.info(f"Fetching tariff for code {code}, country {country_code}")

            # Кеширане - проверяваме дали има актуална стойност
            # САМО ако не е принудително обновяване
            cache_duration = self.env.company.l10n_bg_taric_cache_duration * 3600
            if (product.l10n_bg_tariff_last_update and
                product.l10n_bg_tariff_rate is not False and
                product.l10n_bg_tariff_rate != 0.0 and
                (fields.Datetime.now() - product.l10n_bg_tariff_last_update).total_seconds() < cache_duration):
                _logger.info(f"Using cached rate {product.l10n_bg_tariff_rate} for product {product.id}")
                continue

            # Fetch rate (вече връща decimal формат 0.50 = 50%)
            try:
                dummy_line = MoveLine.new({'product_id': product.id})
                rate = dummy_line._fetch_tariff_rate(code[:8], country_code)
                l10n_bg_tariff_description = dummy_line.l10n_bg_tariff_description

                if l10n_bg_tariff_description:
                    product.l10n_bg_tariff_description = l10n_bg_tariff_description

                if rate is not None:
                    # rate вече е в decimal формат (0.50 за 50%)
                    _logger.info(f"Fetched rate {rate} ({rate * 100}%) for product {product.id}")
                    product.l10n_bg_tariff_rate = rate
                    product.l10n_bg_tariff_last_update = fields.Datetime.now()
                else:
                    _logger.warning(f"No rate found for product {product.id}, using 0.0")
                    product.l10n_bg_tariff_rate = 0.0

            except Exception as e:
                _logger.error(f"Error fetching tariff rate for product {product.id}: {e}", exc_info=True)
                product.l10n_bg_tariff_rate = 0.0

    def _inverse_l10n_bg_tariff_rate(self):
        """Позволява ръчно задаване на тарифна ставка"""
        for product in self:
            if product.l10n_bg_tariff_rate is not False:
                _logger.info(f"Setting manual rate {product.l10n_bg_tariff_rate} for product {product.id}")
                # Запазваме ръчно въведената стойност
                # Ако потребителят въведе през UI с percentage widget,
                # стойността вече ще е в decimal формат
                product.l10n_bg_tariff_rate_manual = product.l10n_bg_tariff_rate
                product.l10n_bg_tariff_last_update = fields.Datetime.now()

    def action_update_tariff_rate(self):
        """Обновява тарифната ставка за избраните продукти"""
        _logger.info(f"Manual update requested for {len(self)} products")

        # ВАЖНО: Изчистваме и ръчната ставка И кеша за да форсираме обновяване от API
        for product in self:
            _logger.info(f"Clearing cache and manual rate for product {product.id}: {product.name}")
            _logger.info(f"  Current manual rate: {product.l10n_bg_tariff_rate_manual}")
            _logger.info(f"  Current rate: {product.l10n_bg_tariff_rate}")

            product.write({
                'l10n_bg_tariff_rate_manual': 0.0,  # <-- ИЗЧИСТВАМЕ ръчната ставка!
                'l10n_bg_tariff_last_update': False,
            })

        # Trigger compute
        self._compute_l10n_bg_tariff_rate()

        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'success',
                'message': f'Обновени тарифни ставки за {len(self)} продукта от EU TARIC',
                'sticky': False,
            }
        )

    def action_clear_manual_tariff_rate(self):
        """Изчиства ръчно въведените тарифни ставки и обновява автоматично"""
        _logger.info(f"Clearing manual rates for {len(self)} products")

        for product in self:
            product.write({
                'l10n_bg_tariff_rate_manual': 0.0,
                'l10n_bg_tariff_last_update': False,
            })

        self._compute_l10n_bg_tariff_rate()

        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'success',
                'message': f'Изчистени ръчни ставки за {len(self)} продукта и обновени автоматично',
                'sticky': False,
            }
        )
