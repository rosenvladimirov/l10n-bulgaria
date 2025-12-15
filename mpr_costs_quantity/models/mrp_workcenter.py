# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    labor_cost_method = fields.Selection([
        ('hour', 'Use base on hour cost'),
        ('quantity', 'Use base on quantity cost'),
    ], string='Cost Method',
       default='hour',
       help='Determines how to calculate labor/machine cost:\n'
            '- hour: uses costs_hour from work center\n'
            '- quantity: uses quantity_cost from work center')

    costs_quantity = fields.Float(
        string='Cost per single',
        help='Single produced unit cost.',
        tracking=True
    )
