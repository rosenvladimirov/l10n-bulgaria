# -*- coding: utf-8 -*-
"""zebra.reader — Zebra / Symbol Scanners record."""

from odoo import _, api, fields, models


class ZebraReader(models.Model):
    _name = 'zebra.reader'
    _description = 'Zebra / Symbol Scanners'
    _order = 'name'

    name = fields.Char(required=True)
    proxy_id = fields.Many2one(
        'erpnet.fp.proxy', required=True, ondelete='cascade', index=True)
    template_id = fields.Many2one('zebra.reader.template',
        string='Model Template')
    active = fields.Boolean(default=True)
    serial_number = fields.Char()
    firmware = fields.Char()

    transport = fields.Selection([('serial', 'Serial'), ('usb_hid', 'USB HID'), ('bluetooth', 'Bluetooth')],
        default='usb_hid', required=True)
    port = fields.Char()
    baudrate = fields.Integer(default=9600)
    network_host = fields.Char()
    network_port = fields.Integer(default=4001)
    bluetooth_address = fields.Char()

    driver = fields.Char(default='zebra.scanner')
    notes = fields.Html()

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.driver = self.template_id.driver or 'zebra.scanner'
            self.transport = self.template_id.default_transport or 'usb_hid'

    @api.model
    def get_config_payload(self):
        entries = []
        for r in self.search([('active', '=', True)]):
            sid = (r.serial_number or r.name).lower().replace(' ', '_')
            entry = {
                'id': sid,
                'driver': r.driver or 'zebra.scanner',
                'transport': r.transport,
            }
            if r.transport == 'serial':
                entry['port'] = r.port or '/dev/ttyUSB0'
                entry['baudrate'] = r.baudrate or 9600
            elif r.transport == 'network':
                entry['host'] = r.network_host or ''
                entry['port'] = r.network_port or 4001
            elif r.transport == 'bluetooth':
                entry['bluetooth_address'] = r.bluetooth_address or ''
            entries.append(entry)
        return entries
