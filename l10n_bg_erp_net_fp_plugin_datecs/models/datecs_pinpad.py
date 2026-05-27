# -*- coding: utf-8 -*-
"""datecs.pinpad — pinpad terminal record (BluePad-55, etc.)."""

from odoo import _, api, fields, models


class DatecsPinpad(models.Model):
    _name = 'datecs.pinpad'
    _description = 'Datecs Pinpad Terminal'
    _order = 'name'

    name = fields.Char(required=True)
    proxy_id = fields.Many2one(
        'erpnet.fp.proxy', required=True, ondelete='cascade', index=True)
    template_id = fields.Many2one('datecs.pinpad.template',
        string='Model Template')
    active = fields.Boolean(default=True)

    # Identification
    serial_number = fields.Char(help='Datecs pinpad serial (DA054852).')
    firmware = fields.Char()

    # Connection
    transport = fields.Selection([
        ('serial', 'Serial'),
        ('bluetooth', 'Bluetooth (BLE)'),
        ('tcp', 'TCP'),
    ], default='bluetooth', required=True)
    port = fields.Char()
    bluetooth_address = fields.Char(string='BLE MAC')
    tcp_host = fields.Char()
    tcp_port = fields.Integer(default=8003)

    # Driver
    driver = fields.Char(default='datecs.pinpad')

    notes = fields.Html()

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.driver = self.template_id.driver or 'datecs.pinpad'
            self.transport = self.template_id.default_transport or 'bluetooth'

    @api.model
    def get_config_payload(self):
        """Generate proxy pinpads: section."""
        entries = []
        for pp in self.search([('active', '=', True)]):
            sid = (pp.serial_number or pp.name).lower().replace(' ', '_')
            entry = {
                'id': f'pinpad_{sid}',
                'driver': pp.driver or 'datecs.pinpad',
                'transport': pp.transport,
            }
            if pp.transport == 'serial':
                entry['port'] = pp.port or '/dev/ttyACM0'
            elif pp.transport == 'bluetooth':
                entry['bluetooth_address'] = pp.bluetooth_address or ''
            elif pp.transport == 'tcp':
                entry['host'] = pp.tcp_host or ''
                entry['port'] = pp.tcp_port or 8003
            entries.append(entry)
        return entries
