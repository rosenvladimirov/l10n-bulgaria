# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""cfx.endpoint — една CFX/AMQP subscription цел за proxy-то.

Всеки запис = един CFX endpoint (машина/брокер), който proxy-то
трябва да абонира. `get_config_payload()` генерира `cfx:` секцията за
push_config командата — точно като datecs.printer.get_config_payload().

CFX е ЕДИН стандарт за ВСИЧКИ машини — machine_kind различава само
къде отиват статистиките (REST audit routing), не транспорта.
"""

from odoo import _, api, fields, models

# Споделени selection-и — import-ват се и в template + stat моделите.
MACHINE_KINDS = [
    ('europlacer', 'Europlacer (SMT placement)'),
    ('parmi', 'PARMI (SPI / AOI inspection)'),
    ('oven', 'Reflow oven'),
    ('laser', 'Laser (marking / cutting)'),
    ('generic', 'Generic CFX machine'),
]

TRANSPORTS = [
    ('broker', 'RabbitMQ broker (AMQP 1.0)'),
    ('p2p', 'AMQP 1.0 peer-to-peer'),
]


def _split_topics(raw):
    """Раздели topics Char (comma/whitespace/newline) на чист list."""
    if not raw:
        return []
    parts = raw.replace(',', ' ').replace('\n', ' ').split()
    return [p.strip() for p in parts if p.strip()]


class CfxEndpoint(models.Model):
    _name = 'cfx.endpoint'
    _description = 'CFX-IPC Endpoint (machine / broker subscription)'
    _order = 'proxy_id, name'

    name = fields.Char(required=True)
    proxy_id = fields.Many2one(
        'erpnet.fp.proxy', required=True, ondelete='cascade', index=True,
        help='Proxy that hosts the CFX listener for this endpoint.')
    template_id = fields.Many2one(
        'cfx.endpoint.template', string='Machine Template',
        help='Known CFX machine type (Europlacer, PARMI, oven, laser).')
    active = fields.Boolean(default=True)

    machine_kind = fields.Selection(
        MACHINE_KINDS, required=True, default='generic',
        help='Machine family. Only affects REST/audit statistics routing; '
             'the live WS → mrp.workorder path is identical for all kinds.')
    transport = fields.Selection(
        TRANSPORTS, required=True, default='broker',
        help='How the proxy reaches this endpoint: a RabbitMQ broker '
             '(AMQP 1.0) or a raw AMQP 1.0 peer-to-peer listener.')

    amqp_uri = fields.Char(
        string='AMQP URI',
        help='Connection URI, e.g. amqp://user:pass@host:5672/ for a broker, '
             'or amqp://0.0.0.0:5672 for a P2P listener bind.')
    cfx_handle = fields.Char(
        string='CFX Handle',
        help='CFX Handle reported by the machine '
             '(e.g. Europlacer.Line1.RC or Parmi.SPI.01).')
    topics = fields.Char(
        help='CFX topics/queues to subscribe, space- or comma-separated. '
             'Empty = subscribe to the machine default topic.')

    notes = fields.Html()

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            tpl = self.template_id
            self.machine_kind = tpl.machine_kind or self.machine_kind
            self.transport = tpl.default_transport or self.transport
            if tpl.default_topics and not self.topics:
                self.topics = tpl.default_topics

    def action_apply_template(self):
        """Приложи template default-ите (без да газим вече попълнени)."""
        for rec in self:
            tpl = rec.template_id
            if not tpl:
                continue
            if tpl.machine_kind:
                rec.machine_kind = tpl.machine_kind
            if tpl.default_transport:
                rec.transport = tpl.default_transport
            if tpl.default_topics and not rec.topics:
                rec.topics = tpl.default_topics

    @api.model
    def action_import_from_proxies(self):
        """Чете erpnet.fp.proxy.device с kind='cfx' и създава cfx.endpoint
        за всеки идентификатор който още не съществува. Идемпотентно."""
        Device = self.env['erpnet.fp.proxy.device'].sudo()
        devices = Device.search([('kind', '=', 'cfx')])
        created = 0
        skipped = 0
        for dev in devices:
            ident = (dev.identifier or '').strip()
            if not ident:
                continue
            exists = self.search([
                ('proxy_id', '=', dev.proxy_id.id),
                ('cfx_handle', '=', ident),
            ], limit=1)
            if exists:
                skipped += 1
                continue
            self.create({
                'name': f'CFX {ident}',
                'cfx_handle': ident,
                'proxy_id': dev.proxy_id.id,
                'machine_kind': 'generic',
            })
            created += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if created else 'info',
                'title': _('Import from Proxy'),
                'message': _(
                    'Imported: %(c)s new endpoint(s); skipped %(s)s '
                    'existing; scanned %(t)s CFX device(s).',
                    c=created, s=skipped, t=len(devices)),
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'cfx.endpoint',
                    'view_mode': 'list,form',
                },
            },
        }

    @api.model
    def get_config_payload(self):
        """Return ALL active endpoints as the proxy `cfx:` section.

        Consumed by erpnet.fp.proxy._collect_push_section('cfx') →
        push_config command drained by the proxy heartbeat. Wire format
        mirrors datecs.printer.get_config_payload(): a list[dict]."""
        entries = []
        for e in self.search([('active', '=', True)]):
            entries.append({
                'id': (e.cfx_handle or e.name).lower().replace(' ', '_'),
                'cfx_handle': e.cfx_handle or '',
                'amqp_uri': e.amqp_uri or '',
                'transport': e.transport,
                'machine_kind': e.machine_kind,
                'topics': _split_topics(e.topics),
            })
        return entries
