# -*- coding: utf-8 -*-
"""datecs.pinpad.template — каталог на known Datecs pinpads."""

from odoo import fields, models


class DatecsPinpadTemplate(models.Model):
    _name = 'datecs.pinpad.template'
    _description = 'Datecs Pinpad Template'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    driver = fields.Char(default='datecs.pinpad')
    default_transport = fields.Selection([
        ('serial', 'Serial'),
        ('bluetooth', 'Bluetooth'),
        ('tcp', 'TCP'),
    ], default='bluetooth')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Template code must be unique.'),
    ]
