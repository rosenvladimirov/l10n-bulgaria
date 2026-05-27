# -*- coding: utf-8 -*-
"""datecs.printer — fiscal printer record (DP-150 / FP-700MX / BlueCash).

Same pattern като polimex.controller — operator UI запис, proxy YAML
generation чрез get_config_payload().
"""

from odoo import _, api, fields, models


_TRANSPORT = [
    ('serial', 'Serial (USB/RS-232)'),
    ('network', 'Network (TCP)'),
    ('bluetooth', 'Bluetooth (BLE)'),
]


class DatecsPrinter(models.Model):
    _name = 'datecs.printer'
    _description = 'Datecs Fiscal Printer'
    _order = 'name'

    name = fields.Char(required=True)
    proxy_id = fields.Many2one(
        'erpnet.fp.proxy', required=True, ondelete='cascade', index=True)
    template_id = fields.Many2one(
        'datecs.printer.template', string='Model Template',
        help='Datecs printer model (DP-150, FP-700MX, BlueCash, etc.).')
    active = fields.Boolean(default=True)

    # Identification
    serial_number = fields.Char(string='Serial Number',
        help='Datecs printer serial (DA052093, DA054852, etc.).')
    firmware = fields.Char()

    # Connection
    transport = fields.Selection(
        _TRANSPORT, default='serial', required=True)
    port = fields.Char(string='Serial Port',
        help="E.g. /dev/ftdi_serial, COM3, /dev/ttyACM0")
    baudrate = fields.Integer(default=115200)
    network_host = fields.Char(string='Network Host',
        help='TCP host (за transport=network).')
    network_port = fields.Integer(string='TCP Port', default=4999)
    bluetooth_address = fields.Char(string='Bluetooth Address (MAC)',
        help='BLE MAC за BlueCash mobile printers.')

    # Operator / cashier
    operator = fields.Char(default='1',
        help='Operator slot (1-30 за повечето Datecs).')
    operator_password = fields.Char(default='0000')

    # Driver
    driver = fields.Char(default='datecs.isl',
        help='Proxy driver name (datecs.isl, datecs.pm, datecs.fpr).')
    plu_mode = fields.Boolean(string='PLU-only mode',
        help='Force PLU-only (per memory: FP-700MX requires это).')

    # Reverse o2m към polimex-style parts (printer има само 1 print head,
    # но има parts за integrated peripherals: scanner, customer display)
    notes = fields.Html()

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.driver = self.template_id.driver or 'datecs.isl'
            self.transport = self.template_id.default_transport or 'serial'
            self.plu_mode = self.template_id.plu_mode

    def action_apply_template(self):
        """Apply template parameters to controller."""
        for rec in self:
            if not rec.template_id:
                continue
            tpl = rec.template_id
            if tpl.driver and not rec.driver:
                rec.driver = tpl.driver
            if tpl.default_transport and not rec.transport:
                rec.transport = tpl.default_transport
            rec.plu_mode = tpl.plu_mode

    def action_compare_template(self):
        """Diff между record и template — read-only.
        Не пише, не push-ва конфиг — само notification със списък
        на разликите."""
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
        # mapping: record_field → (current, template_value, label)
        rows = [
            ('driver', self.driver or '', tpl.driver or '', 'Driver'),
            ('transport', self.transport or '', tpl.default_transport or '',
             'Transport'),
            ('plu_mode', str(self.plu_mode), str(tpl.plu_mode), 'PLU mode'),
        ]
        diffs = [r for r in rows if r[1] != r[2]]
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
        for _f, cur, tplv, label in diffs:
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
    def get_config_payload(self):
        """Return ALL active printers as proxy printers: section."""
        entries = []
        for p in self.search([('active', '=', True)]):
            entry = {
                'id': (p.serial_number or p.name).lower().replace(' ', '_'),
                'driver': p.driver or 'datecs.isl',
                'transport': p.transport,
                'operator': p.operator or '1',
                'password': p.operator_password or '0000',
            }
            if p.transport == 'serial':
                entry['port'] = p.port or '/dev/ttyACM0'
                entry['baudrate'] = p.baudrate or 115200
            elif p.transport == 'network':
                entry['host'] = p.network_host or ''
                entry['port'] = p.network_port or 4999
            elif p.transport == 'bluetooth':
                entry['bluetooth_address'] = p.bluetooth_address or ''
            if p.plu_mode:
                entry['plu_mode'] = True
            entries.append(entry)
        return entries
