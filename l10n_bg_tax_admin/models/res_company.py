from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ТАРИК API настройки
    l10n_bg_taric_api_url = fields.Char(
        string='TARIC API URL',
        default='https://ec.europa.eu/taxation_customs/dds2/taric/api/v1',
        help="URL на Европейската ТАРИК API система"
    )

    l10n_bg_taric_api_enabled = fields.Boolean(
        string='Enable TARIC API',
        default=True,
        help="Активиране на автоматичното търсене в ТАРИК"
    )

    l10n_bg_taric_cache_duration = fields.Integer(
        string='TARIC Cache Duration (hours)',
        default=24,
        help="Колко часа да се кешират тарифните ставки"
    )

    l10n_bg_default_tariff_rate = fields.Float(
        string='Default Tariff Rate (%)',
        default=5.0,
        help="Стандартна тарифна ставка когато не може да се намери в ТАРИК"
    )
