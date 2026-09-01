import logging

from odoo import api, models

from .stock_warehouse import MTO_OPTIONAL_CTX

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get(MTO_OPTIONAL_CTX):
            # Единственото правило без маршрут в двата защитени вика е MTO-то;
            # всички останали носят `route_id` на новосъздадения inter-warehouse
            # маршрут. Затова филтърът не може да изяде нещо легитимно.
            kept = [vals for vals in vals_list if vals.get("route_id")]
            skipped = len(vals_list) - len(kept)
            if skipped:
                _logger.warning(
                    "Skipped %s route-less stock rule(s): the global MTO route is missing.",
                    skipped,
                )
                vals_list = kept
        return super().create(vals_list)
