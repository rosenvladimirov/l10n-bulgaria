# -*- coding: utf-8 -*-
"""cas.scale.template — catalog of known CAS Scales."""

from odoo import fields, models


class CasScaleTemplate(models.Model):
    _name = 'cas.scale.template'
    _description = 'CAS Scales Template'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    driver = fields.Char(default='cas.scale')
    default_transport = fields.Selection([('serial', 'Serial RS-232'), ('network', 'Network')],
        default='serial')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Template code must be unique.'),
    ]
