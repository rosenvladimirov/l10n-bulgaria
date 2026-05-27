# -*- coding: utf-8 -*-
"""zebra.reader.template — catalog of known Zebra / Symbol Scanners."""

from odoo import fields, models


class ZebraReaderTemplate(models.Model):
    _name = 'zebra.reader.template'
    _description = 'Zebra / Symbol Scanners Template'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    driver = fields.Char(default='zebra.scanner')
    default_transport = fields.Selection([('serial', 'Serial'), ('usb_hid', 'USB HID'), ('bluetooth', 'Bluetooth')],
        default='usb_hid')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Template code must be unique.'),
    ]
