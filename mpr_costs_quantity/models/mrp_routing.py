# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools import float_round


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    def _get_duration_expected(self, product, quantity, unit=False, workcenter=False):
        # Извикваме супер класа за базовата продължителност
        res = super()._get_duration_expected(product, quantity, unit, workcenter)

        # Добавяме допълнителна логика
        product = product or self.bom_id.product_tmpl_id
        if self._skip_operation_line(product):
            return res
        unit = unit or product.uom_id
        quantity = self.bom_id.product_uom_id._compute_quantity(quantity, unit)
        workcenter = workcenter or self.workcenter_id
        capacity = workcenter._get_capacity(product)
        cycle_number = float_round(quantity / capacity, precision_digits=0, rounding_method='UP')
        res += cycle_number * self.time_cycle * 100.0 / workcenter.time_efficiency

        return res

    def _compute_operation_cost(self):
        # Вземаме базовата цена от супер класа
        res = super()._compute_operation_cost()

        workcenter = self.workcenter_id

        # Добавяме цена базирана на количество, ако е зададена
        if hasattr(workcenter, 'labor_cost_method') and workcenter.labor_cost_method == 'quantity':
            quantity = self.env.context.get('op_quantity', 0)
            product = self.env.context.get('op_product')

            if quantity and product:
                capacity = workcenter._get_capacity(product)
                cycle_number = float_round(quantity / capacity, precision_digits=0, rounding_method='UP')
                res += cycle_number * workcenter.costs_quantity
            else:
                # Ако нямаме количество, използваме costs_quantity директно
                res += workcenter.costs_quantity

        return res
