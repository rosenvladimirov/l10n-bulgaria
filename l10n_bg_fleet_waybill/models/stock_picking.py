# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _

import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Picking(models.Model):
    _inherit = "stock.picking"

    waybill_id = fields.Many2one('fleet.vehicle.waybill', 'Waybill')
