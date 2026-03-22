# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Автоматична класификация
    auto_classify_enabled = fields.Boolean(
        string='Enable Auto-Classification',
        config_parameter='taric_ai.auto_classify_enabled',
        default=False,
        help='Automatically suggest TARIC codes when creating new products'
    )

    auto_apply_high_confidence = fields.Boolean(
        string='Auto-apply High Confidence',
        config_parameter='taric_ai.auto_apply_high_confidence',
        default=False,
        help='Automatically apply AI suggestions with confidence > 95%'
    )

    min_confidence_threshold = fields.Float(
        string='Minimum Confidence Threshold %',
        config_parameter='taric_ai.min_confidence_threshold',
        default=80.0,
        help='Minimum confidence score to show AI suggestions'
    )
