# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

import logging
_logger = logging.getLogger(__name__)

class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    name = fields.Char(translate=True)
