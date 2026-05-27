# -*- coding: utf-8 -*-
"""datecs.printer.template — каталог на known Datecs fiscal printers."""

from odoo import fields, models


class DatecsPrinterTemplate(models.Model):
    _name = 'datecs.printer.template'
    _description = 'Datecs Printer Template (model catalog)'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    driver = fields.Char(
        default='datecs.isl',
        help='Default proxy driver: datecs.isl / datecs.pm / datecs.fpr')
    default_transport = fields.Selection([
        ('serial', 'Serial'),
        ('network', 'Network'),
        ('bluetooth', 'Bluetooth'),
    ], default='serial')
    plu_mode = fields.Boolean(default=False,
        help='Force PLU-only mode (e.g. FP-700MX).')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Template code must be unique.'),
    ]
