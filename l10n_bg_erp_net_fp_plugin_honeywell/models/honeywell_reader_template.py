# -*- coding: utf-8 -*-
"""honeywell.reader.template — catalog of known Honeywell Scanners."""

from odoo import fields, models


class HoneywellReaderTemplate(models.Model):
    _name = 'honeywell.reader.template'
    _description = 'Honeywell Scanners Template'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    driver = fields.Char(default='honeywell.scanner')
    default_transport = fields.Selection([('serial', 'Serial (RS-232/USB)'), ('usb_hid', 'USB HID (keyboard wedge)'), ('network', 'Network')],
        default='serial')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Template code must be unique.'),
    ]
