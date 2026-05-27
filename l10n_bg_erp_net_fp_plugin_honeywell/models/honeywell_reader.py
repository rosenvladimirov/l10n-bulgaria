# -*- coding: utf-8 -*-
"""honeywell.reader — Honeywell Scanners record."""

from odoo import _, api, fields, models


class HoneywellReader(models.Model):
    _name = 'honeywell.reader'
    _description = 'Honeywell Scanners'
    _order = 'name'

    name = fields.Char(required=True)
    proxy_id = fields.Many2one(
        'erpnet.fp.proxy', required=True, ondelete='cascade', index=True)
    template_id = fields.Many2one('honeywell.reader.template',
        string='Model Template')
    active = fields.Boolean(default=True)
    serial_number = fields.Char()
    firmware = fields.Char()

    transport = fields.Selection([('serial', 'Serial (RS-232/USB)'), ('usb_hid', 'USB HID (keyboard wedge)'), ('network', 'Network')],
        default='serial', required=True)
    port = fields.Char()
    baudrate = fields.Integer(default=9600)
    network_host = fields.Char()
    network_port = fields.Integer(default=4001)
    bluetooth_address = fields.Char()

    driver = fields.Char(default='honeywell.scanner')
    notes = fields.Html()

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.driver = self.template_id.driver or 'honeywell.scanner'
            self.transport = self.template_id.default_transport or 'serial'

    @api.model
    def get_config_payload(self):
        entries = []
        for r in self.search([('active', '=', True)]):
            sid = (r.serial_number or r.name).lower().replace(' ', '_')
            entry = {
                'id': sid,
                'driver': r.driver or 'honeywell.scanner',
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
