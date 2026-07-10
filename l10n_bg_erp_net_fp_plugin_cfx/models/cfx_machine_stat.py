# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""cfx.machine.stat — generic per-message статистически запис.

Единен приемник за parmi/oven/laser/generic машините (Europlacer има
свой богат схема-модел europlacer.trac в mrp_europlacer_trac). Държи
общите числови метрики + raw payload за по-нататъшен разбор, докато
per-machine field-set-овете се дефинират при onboarding на всяка
машина (виж PLAN §6).
"""

from odoo import api, fields, models

from .cfx_endpoint import MACHINE_KINDS


class CfxMachineStat(models.Model):
    _name = 'cfx.machine.stat'
    _description = 'CFX Machine Statistic (generic per-message record)'
    _order = 'event_time desc, id desc'
    _rec_name = 'display_name'

    proxy_id = fields.Many2one(
        'erpnet.fp.proxy', ondelete='cascade', index=True)
    endpoint_id = fields.Many2one(
        'cfx.endpoint', ondelete='set null', index=True)
    machine_kind = fields.Selection(
        MACHINE_KINDS, required=True, default='generic', index=True)
    cfx_handle = fields.Char(string='CFX Handle')
    message_name = fields.Char(
        string='CFX Message',
        help='CFX message class name (e.g. UnitsInspected, StationStateChanged).')
    transaction_id = fields.Char(string='CFX TransactionId', index=True)
    workorder_ref = fields.Char(
        string='Work Order Reference',
        help='mrp.workorder name/reference this event relates to, if any.')
    event_time = fields.Datetime(default=fields.Datetime.now, index=True)

    # Общи числови метрики (най-често срещаните CFX стойности)
    quantity = fields.Float(
        help='Count of units/materials in this event (e.g. UnitsInspected).')
    defect_count = fields.Integer(
        help='Number of defects/faults reported in this event.')
    measured_value = fields.Float(
        help='A single scalar measurement (e.g. peak temperature, offset).')
    unit = fields.Char(help='Unit for measured_value (°C, mm, %, ...).')

    # ── Inspection summary (попълва се от cfx_extractors при AOI/SPI) ──
    inspection_method = fields.Char(
        string='Inspection Method',
        help='CFX InspectionMethod (AOI, SPI, X-Ray, Human, ...).')
    recipe_name = fields.Char(string='Recipe')
    recipe_revision = fields.Char(string='Recipe Rev.')
    operator_name = fields.Char(string='Operator')
    station_state = fields.Char(string='Station State')
    units_total = fields.Integer(string='Units')
    units_passed = fields.Integer(string='Units Passed')
    units_failed = fields.Integer(string='Units Failed')
    defects_total = fields.Integer(string='Defects')
    measurements_total = fields.Integer(string='Measurements')

    # ── Детайлни редове (реалната информация от JSON-а) ──
    unit_ids = fields.One2many(
        'cfx.inspection.unit', 'stat_id', string='Inspected Units')
    defect_ids = fields.One2many(
        'cfx.inspection.defect', 'stat_id', string='Defects')
    measurement_ids = fields.One2many(
        'cfx.inspection.measurement', 'stat_id', string='Measurements')

    payload_json = fields.Text(
        string='Raw Payload',
        help='Full CFX event data dict as received (JSON).')

    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('machine_kind', 'message_name', 'cfx_handle')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = ' · '.join(
                p for p in (rec.machine_kind, rec.message_name,
                            rec.cfx_handle) if p) or 'CFX event'
