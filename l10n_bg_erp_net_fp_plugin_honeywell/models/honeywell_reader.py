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
    def action_import_from_proxies(self):
        """Чете erpnet.fp.proxy.device с kind='reader' и създава
        honeywell.reader запис за всеки, който започва с Honeywell
        prefix (HW/1470/1250/5145/VG)."""
        Device = self.env['erpnet.fp.proxy.device'].sudo()
        Template = self.env['honeywell.reader.template'].sudo()
        devices = Device.search([('kind', '=', 'reader')])
        templates = Template.search([])
        tpl_map = {tpl.code: tpl for tpl in templates}
        # First match wins; longer prefixes first.
        prefix_hints = [
            ('HW_1470', 'hw_1470g'),
            ('HW1470',  'hw_1470g'),
            ('1470',    'hw_1470g'),
            ('HW_1250', 'hw_1250g'),
            ('HW1250',  'hw_1250g'),
            ('1250',    'hw_1250g'),
            ('VG_1250', 'hw_1250g'),  # Voyager 1250G
            ('VOYAGER', 'hw_1250g'),
            ('HW_5145', 'hw_5145'),
            ('5145',    'hw_5145'),
            ('ECLIPSE', 'hw_5145'),
            ('HONEYWELL', 'hw_1470g'),  # generic fallback
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
                # Не е Honeywell — друг плъгин (Zebra) ще се занимае
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
                'name': f'Honeywell {ident}',
                'serial_number': ident,
                'proxy_id': dev.proxy_id.id,
                'template_id': tpl.id,
                'driver': tpl.driver,
                'transport': tpl.default_transport or 'serial',
            })
            created += 1
        msg_lines = [
            _('Imported: %s new reader(s)', created),
            _('Skipped (exists): %s', skipped),
            _('Scanned: %s reader entries', len(devices)),
        ]
        if no_match:
            msg_lines.append(_(
                'No Honeywell prefix match (try Zebra import or manual): %s',
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
                    'res_model': 'honeywell.reader',
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
