# -*- coding: utf-8 -*-
"""cas.scale — CAS Scales record."""

from odoo import _, api, fields, models


class CasScale(models.Model):
    _name = 'cas.scale'
    _description = 'CAS Scales'
    _order = 'name'

    name = fields.Char(required=True)
    proxy_id = fields.Many2one(
        'erpnet.fp.proxy', required=True, ondelete='cascade', index=True)
    template_id = fields.Many2one('cas.scale.template',
        string='Model Template')
    active = fields.Boolean(default=True)
    serial_number = fields.Char()
    firmware = fields.Char()

    transport = fields.Selection([('serial', 'Serial RS-232'), ('network', 'Network')],
        default='serial', required=True)
    port = fields.Char()
    baudrate = fields.Integer(default=9600)
    network_host = fields.Char()
    network_port = fields.Integer(default=4001)
    bluetooth_address = fields.Char()

    driver = fields.Char(default='cas.scale')
    notes = fields.Html()

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.driver = self.template_id.driver or 'cas.scale'
            self.transport = self.template_id.default_transport or 'serial'

    @api.model
    def action_import_from_proxies(self):
        """Чете erpnet.fp.proxy.device с kind='scale' и създава
        cas.scale запис за всеки CAS-prefix serial."""
        Device = self.env['erpnet.fp.proxy.device'].sudo()
        Template = self.env['cas.scale.template'].sudo()
        devices = Device.search([('kind', '=', 'scale')])
        templates = Template.search([])
        tpl_map = {tpl.code: tpl for tpl in templates}
        prefix_hints = [
            ('CAS_PR', 'cas_pr_plus'),
            ('PR_PLUS', 'cas_pr_plus'),
            ('PRPLUS', 'cas_pr_plus'),
            ('CL5000', 'cas_cl5000'),
            ('CL_5000', 'cas_cl5000'),
            ('CAS_BENCH', 'cas_bench'),
            ('CAS', 'cas_pr_plus'),  # generic fallback
        ]
        created, skipped, no_match = 0, 0, []
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
                'name': f'CAS {ident}',
                'serial_number': ident,
                'proxy_id': dev.proxy_id.id,
                'template_id': tpl.id,
                'driver': tpl.driver,
                'transport': tpl.default_transport or 'serial',
            })
            created += 1
        lines = [
            _('Imported: %s new scale(s)', created),
            _('Skipped (exists): %s', skipped),
            _('Scanned: %s scale entries', len(devices)),
        ]
        if no_match:
            lines.append(_('No CAS prefix match: %s', ', '.join(no_match[:5])))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if created else 'info',
                'title': _('Import from Proxy'),
                'message': '\n'.join(lines),
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'cas.scale',
                    'view_mode': 'kanban,list,form',
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
                'driver': r.driver or 'cas.scale',
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
