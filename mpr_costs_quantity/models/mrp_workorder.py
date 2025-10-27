# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    costs_quantity = fields.Float(
        string='Cost per quantity',
        default=0.0, aggregator="avg")
        # Technical field to store the hourly cost of workcenter at time of work order completion (i.e. to keep a consistent cost).'

    def _cal_cost(self, date=False):
        """Override на базовия метод за изчисляване на разходи

        Базовата логика:
        - Използва workorder.time_ids за реалното отработено време
        - Умножава по workcenter.costs_hour

        Нашето разширение:
        - Ако workcenter.labor_cost_method == 'employee'
        - Използваме employee.hourly_cost вместо workcenter.costs_hour
        """
        total = 0
        for workorder in self:
            workcenter_id = workorder.workcenter_id
            if workcenter_id.labor_cost_method == 'hour':
                # Извикваме базовия метод само за този конкретен workorder
                total += super(MrpWorkorder, workorder)._cal_cost(date=date)
            elif workcenter_id.labor_cost_method == 'quantity':
                total += workcenter_id.costs_quantity / workcenter_id.default_capacity * workorder.qty_producing
        return total

    def button_finish(self):
        res = super(MrpWorkorder, self).button_finish()
        for wo in self:
            workcenter_id = wo.workcenter_id
            wo.costs_quantity = workcenter_id.costs_quantity/workcenter_id.default_capacity
        return res

    def button_done(self):
        super().button_done()
        for wo in self:
            workcenter_id = wo.workcenter_id
            wo.costs_quantity = workcenter_id.costs_quantity/workcenter_id.default_capacity

    def _compute_expected_operation_cost(self, without_employee_cost=False):
        if self.workcenter_id.labor_cost_method == 'hour':
            return super()._compute_expected_operation_cost(without_employee_cost=without_employee_cost)
        else:
            return self.costs_quantity * self.qty_producing

    def _compute_current_operation_cost(self):
        if self.workcenter_id.labor_cost_method == 'hour':
            return super()._compute_current_operation_cost()
        else:
            return self.costs_quantity * self.qty_producing

    def _get_current_theorical_operation_cost(self, without_employee_cost=False):
        if self.workcenter_id.labor_cost_method == 'hour':
            return super()._get_current_theorical_operation_cost(without_employee_cost=without_employee_cost)
        else:
            return self.costs_quantity * self.qty_producing
