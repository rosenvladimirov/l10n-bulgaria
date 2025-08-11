# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fiscal_printer_id = fields.Many2one(related='pos_config_id.fiscal_printer_id', readonly=False)
    auto_fiscal_printing = fields.Boolean(related='pos_config_id.auto_fiscal_printing', readonly=False)
