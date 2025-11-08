from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Полето hs_code вече съществува в stock_delivery модула
    # Добавяме само помощна информация

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

    @api.depends('hs_code', 'country_of_origin', 'l10n_bg_tariff_rate_manual')
    def _compute_l10n_bg_tariff_rate(self):
        """Изчислява тарифната ставка за продукта"""
        MoveLine = self.env['account.move.line']
        for product in self:
            # Ако има ръчно въведена ставка, използваме нея
            if product.l10n_bg_tariff_rate_manual:
                product.l10n_bg_tariff_rate = product.l10n_bg_tariff_rate_manual
                continue

            if not product.hs_code:
                product.l10n_bg_tariff_rate = 0.0
                continue

            # Използваме логиката от account.move.line
            country_code = product.country_of_origin.code if product.country_of_origin else 'CN'

            # Кеширане - проверяваме дали има актуална стойност
            cache_duration = self.env.company.l10n_bg_taric_cache_duration * 3600
            if (product.l10n_bg_tariff_last_update and
                product.l10n_bg_tariff_rate and
                (fields.Datetime.now() - product.l10n_bg_tariff_last_update).total_seconds() < cache_duration):
                continue

            # Fetch rate
            dummy_line = MoveLine.new({'product_id': product.id})
            rate = dummy_line._fetch_tariff_rate(product.hs_code[:8], country_code)
            l10n_bg_tariff_description = dummy_line.l10n_bg_tariff_description

            if l10n_bg_tariff_description:
                product.l10n_bg_tariff_description = l10n_bg_tariff_description

            if rate is not None:
                product.l10n_bg_tariff_rate = rate
                product.l10n_bg_tariff_last_update = fields.Datetime.now()

    def _inverse_l10n_bg_tariff_rate(self):
        """Позволява ръчно задаване на тарифна ставка"""
        for product in self:
            if product.l10n_bg_tariff_rate is not False:
                # Запазваме ръчно въведената стойност
                product.l10n_bg_tariff_rate_manual = product.l10n_bg_tariff_rate
                product.l10n_bg_tariff_last_update = fields.Datetime.now()

    def action_update_tariff_rate(self):
        """Обновява тарифната ставка за избраните продукти"""
        self.l10n_bg_tariff_last_update = False
        self._compute_l10n_bg_tariff_rate()

    def action_clear_manual_tariff_rate(self):
        """Изчиства ръчно въведените тарифни ставки и обновява автоматично"""
        for product in self:
            product.l10n_bg_tariff_rate_manual = 0.0
            product.l10n_bg_tariff_last_update = False
        self._compute_l10n_bg_tariff_rate()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Успех',
                'message': f'Изчистени ръчни ставки за {len(self)} продукта и обновени автоматично',
                'type': 'success',
                'sticky': False,
            }
        }
