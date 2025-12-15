# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.tools import float_round


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    @api.model
    def _get_operation_cost(self, operation, workcenter, duration, quantity=None, product=None):
        # Вземаме базовата цена (базирана на час)
        res = super()._get_operation_cost(operation, workcenter, duration)

        # Добавяме цена базирана на количество, ако е зададена
        if hasattr(workcenter, 'labor_cost_method') and workcenter.labor_cost_method == 'quantity':
            if quantity and product:
                # Използваме същата логика като в _get_duration_expected
                capacity = workcenter._get_capacity(product)
                cycle_number = float_round(quantity / capacity, precision_digits=0, rounding_method='UP')
                res += cycle_number * workcenter.costs_quantity
            else:
                # Ако нямаме количество, използваме costs_quantity директно
                res += workcenter.costs_quantity

        return res
