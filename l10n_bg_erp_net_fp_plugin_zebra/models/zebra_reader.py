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
    def action_import_from_proxies(self):
        """Import readers матчващи Zebra/Symbol prefix."""
        Device = self.env['erpnet.fp.proxy.device'].sudo()
        Template = self.env['zebra.reader.template'].sudo()
        devices = Device.search([('kind', '=', 'reader')])
        templates = Template.search([])
        tpl_map = {tpl.code: tpl for tpl in templates}
        prefix_hints = [
            ('DS_2208', 'zb_ds2208'),
            ('DS2208',  'zb_ds2208'),
            ('DS_3678', 'zb_ds3678'),
            ('DS3678',  'zb_ds3678'),
            ('LS_2208', 'zb_ls2208'),
            ('LS2208',  'zb_ls2208'),
            ('ZEBRA',   'zb_ds2208'),
            ('SYMBOL',  'zb_ls2208'),
        ]
        created = 0
        skipped = 0
        no_match = []
        for dev in devices:
            ident = (dev.identifier or '').strip()
            if not ident:
                continue
            tpl = False
            for prefix, code in prefix_hints:
                if ident.upper().startswith(prefix):
                    tpl = tpl_map.get(code)
                    if tpl:
                        break
            if not tpl:
                no_match.append(ident)
                continue
            exists = self.search([
                ('proxy_id', '=', dev.proxy_id.id),
                ('serial_number', '=', ident),
            ], limit=1)
            if exists:
                skipped += 1
                continue
            self.create({
                'name': f'Zebra {ident}',
                'serial_number': ident,
                'proxy_id': dev.proxy_id.id,
                'template_id': tpl.id,
                'driver': tpl.driver,
                'transport': tpl.default_transport or 'usb_hid',
            })
            created += 1
        msg_lines = [
            _('Imported: %s new reader(s)', created),
            _('Skipped (exists): %s', skipped),
            _('Scanned: %s reader entries', len(devices)),
        ]
        if no_match:
            msg_lines.append(_(
                'No Zebra prefix match: %s',
                ', '.join(no_match[:5])))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if created else 'info',
                'title': _('Import from Proxy'),
                'message': '\n'.join(msg_lines),
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'zebra.reader',
                    'view_mode': 'list,form',
                },
            },
        }

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
