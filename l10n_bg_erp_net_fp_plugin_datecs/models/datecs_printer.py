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
    def action_import_from_proxies(self):
        """Чете erpnet.fp.proxy.device с kind='printers' и създава
        datecs.printer запис за всеки идентификатор който още не
        съществува. Идемпотент — re-run-ва се safely."""
        Device = self.env['erpnet.fp.proxy.device'].sudo()
        Template = self.env['datecs.printer.template'].sudo()
        proxies_devices = Device.search([('kind', '=', 'printers')])
        # Auto-detect template by serial prefix или fallback
        # tpl_by_prefix: DP-150 → 'DT*' (Datecs DP-150 серийници почват
        # с DT — known от feedback_proxy_device_serial_id_convention)
        templates = Template.search([])
        tpl_map = {tpl.code: tpl for tpl in templates}
        # known mappings (memory: feedback_fp700mx_plu_only_mode_empirical,
        # project_bluecash55_three_bridges)
        prefix_hints = {
            'DT': 'dp150',         # Datecs DP-150 ECR
            'DA052': 'fp700mx',    # Datecs FP-700MX
            'DA054': 'bluecash55', # BlueCash-55 mobile
            'DA050': 'bluecash50', # BlueCash-50
        }
        created = 0
        skipped = 0
        for dev in proxies_devices:
            ident = (dev.identifier or '').strip()
            if not ident:
                continue
            # Дубликат check — по (proxy_id, serial_number)
            exists = self.search([
                ('proxy_id', '=', dev.proxy_id.id),
                ('serial_number', '=', ident),
            ], limit=1)
            if exists:
                skipped += 1
                continue
            tpl = False
            for prefix, code in prefix_hints.items():
                if ident.upper().startswith(prefix):
                    tpl = tpl_map.get(code)
                    break
            vals = {
                'name': f'Datecs {ident}',
                'serial_number': ident,
                'proxy_id': dev.proxy_id.id,
            }
            if tpl:
                vals['template_id'] = tpl.id
                vals['driver'] = tpl.driver
                vals['transport'] = tpl.default_transport or 'serial'
                vals['plu_mode'] = tpl.plu_mode
            self.create(vals)
            created += 1
        msg_lines = [
            _('Imported: %s new printer(s)', created),
            _('Skipped: %s existing record(s)', skipped),
            _('Scanned: %s proxy device entries', len(proxies_devices)),
        ]
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
                    'res_model': 'datecs.printer',
                    'view_mode': 'list,form',
                },
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
