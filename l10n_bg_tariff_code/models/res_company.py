from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_bg_taric_api_url = fields.Char(
        string='TARIC API URL',
        default='https://ec.europa.eu/taxation_customs/dds2/taric/services/taricws',
        help="URL of the European TARIC API system"
    )

    l10n_bg_taric_api_enabled = fields.Boolean(
        string='Enable TARIC API',
        default=True,
        help="Enable automatic TARIC lookup"
    )

    l10n_bg_taric_cache_duration = fields.Integer(
        string='TARIC Cache Duration (hours)',
        default=24,
        help="How many hours to cache tariff rates"
    )

    l10n_bg_default_tariff_rate = fields.Float(
        string='Default Tariff Rate (%)',
        help="Default tariff rate when it cannot be found in TARIC"
    )

    l10n_bg_auto_download = fields.Boolean(
        string='Auto Download',
        help="Download TARIC data automatically"
    )
