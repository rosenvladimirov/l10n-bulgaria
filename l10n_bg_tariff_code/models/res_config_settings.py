from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_bg_taric_api_url = fields.Char(
        related='company_id.l10n_bg_taric_api_url',
        string='TARIC API URL',
        readonly=False,
        help="URL of the European TARIC API system"
    )

    l10n_bg_taric_api_enabled = fields.Boolean(
        related='company_id.l10n_bg_taric_api_enabled',
        string='Enable TARIC API',
        readonly=False,
        help="Enable automatic TARIC lookup"
    )

    l10n_bg_taric_cache_duration = fields.Integer(
        related='company_id.l10n_bg_taric_cache_duration',
        string='TARIC Cache Duration (hours)',
        readonly=False,
        help="How many hours to cache tariff rates"
    )

    l10n_bg_default_tariff_rate = fields.Float(
        related='company_id.l10n_bg_default_tariff_rate',
        string='Default Tariff Rate (%)',
        readonly=False,
        help="Default tariff rate when it cannot be found in TARIC"
    )
