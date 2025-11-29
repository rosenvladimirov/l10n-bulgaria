from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_update_tariff_rate(self):
        """Обновява тарифната ставка за избраните продукт варианти"""
        _logger.info(f"Manual update requested for {len(self)} product variants")

        # Изчистваме кеша за да форсираме обновяване от API
        for product in self:
            _logger.info(f"Clearing cache and manual rate for product variant {product.id}: {product.name}")

            product.product_tmpl_id.write({
                'l10n_bg_tariff_rate_manual': 0.0,
                'l10n_bg_tariff_last_update': False,
            })

        # Trigger compute на template
        self.mapped('product_tmpl_id')._compute_l10n_bg_tariff_rate()

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
        _logger.info(f"Clearing manual rates for {len(self)} product variants")

        for product in self:
            product.product_tmpl_id.write({
                'l10n_bg_tariff_rate_manual': 0.0,
                'l10n_bg_tariff_last_update': False,
            })

        self.mapped('product_tmpl_id')._compute_l10n_bg_tariff_rate()

        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'success',
                'message': f'Изчистени ръчни ставки за {len(self)} продукта и обновени автоматично',
                'sticky': False,
            }
        )
