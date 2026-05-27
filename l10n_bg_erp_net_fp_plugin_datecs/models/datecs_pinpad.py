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

    def action_compare_template(self):
        """Read-only diff срещу template — не пише, не push-ва конфиг."""
        self.ensure_one()
        if not self.template_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': _('No Template'),
                    'message': _('Select a Model Template first.'),
                    'sticky': False,
                },
            }
        tpl = self.template_id
        rows = [
            (self.driver or '', tpl.driver or '', 'Driver'),
            (self.transport or '', tpl.default_transport or '', 'Transport'),
        ]
        diffs = [r for r in rows if r[0] != r[1]]
        if not diffs:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('Match'),
                    'message': _(
                        'All template fields match current values '
                        '(template: %s).', tpl.display_name),
                    'sticky': False,
                },
            }
        lines = [_('Differences vs template "%s":', tpl.display_name)]
        for cur, tplv, label in diffs:
            lines.append(_('• %s: current=%s | template=%s', label, cur, tplv))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'title': _('Template diff'),
                'message': '\n'.join(lines),
                'sticky': True,
            },
        }

    @api.model
    def action_import_from_proxies(self):
        """Чете erpnet.fp.proxy.device с kind='pinpads' и създава
        datecs.pinpad запис за всеки нов serial."""
        Device = self.env['erpnet.fp.proxy.device'].sudo()
        Template = self.env['datecs.pinpad.template'].sudo()
        devices = Device.search([('kind', '=', 'pinpad')])
        templates = Template.search([])
        tpl_map = {tpl.code: tpl for tpl in templates}
        # known prefixes (BluePad-55 устройства = ДП50, серийни като
        # PP* или DA* в зависимост от партида)
        prefix_hints = {
            'PP': 'bluepad55',
            'DA': 'bluepad55',  # повечето BluePad-55 също DA-prefix
        }
        created = 0
        skipped = 0
        for dev in devices:
            ident = (dev.identifier or '').strip()
            if not ident:
                continue
            # pinpad_<serial> е името в proxy; пресмятам serial
            clean = ident
            if clean.startswith('pinpad_'):
                clean = clean[len('pinpad_'):]
            exists = self.search([
                ('proxy_id', '=', dev.proxy_id.id),
                ('serial_number', '=', clean),
            ], limit=1)
            if exists:
                skipped += 1
                continue
            tpl = False
            for prefix, code in prefix_hints.items():
                if clean.upper().startswith(prefix):
                    tpl = tpl_map.get(code)
                    break
            vals = {
                'name': f'Datecs Pinpad {clean}',
                'serial_number': clean,
                'proxy_id': dev.proxy_id.id,
            }
            if tpl:
                vals['template_id'] = tpl.id
                vals['driver'] = tpl.driver
                vals['transport'] = tpl.default_transport or 'bluetooth'
            self.create(vals)
            created += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if created else 'info',
                'title': _('Import from Proxy'),
                'message': '\n'.join([
                    _('Imported: %s new pinpad(s)', created),
                    _('Skipped: %s existing record(s)', skipped),
                    _('Scanned: %s proxy device entries', len(devices)),
                ]),
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'datecs.pinpad',
                    'view_mode': 'list,form',
                },
            },
        }

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
