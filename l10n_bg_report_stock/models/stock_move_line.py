# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        for aggregated_move_line in aggregated_move_lines:
            _logger.info(f"aggregated_move_line: {aggregated_move_line}")
            # lot_id = aggregated_move_lines[aggregated_move_line]['move']
            # aggregated_move_lines[aggregated_move_line]['lot_id'] = lot_id
        return aggregated_move_lines
