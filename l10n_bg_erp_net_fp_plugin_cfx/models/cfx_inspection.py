# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""cfx.inspection.* — детайлни редове от CFX inspection съобщения.

Реалната информация, извлечена от AOI/SPI `UnitsInspected` (виж
cfx_extractors.py), се материализира тук в нормализирани таблици, за да
се вижда в справката/dashboard-а по всеки модел от JSON-а:

    cfx.inspection.unit         — един инспектиран модул/панел
      └ cfx.inspection.defect       — намерен дефект (код/категория/компонент)
      └ cfx.inspection.measurement  — SPI/offset измерване (обем/отклонение)

Всички са read-only отражения на входящите CFX събития — попълват се от
controller-а при ingest, не се редактират ръчно.
"""

from odoo import fields, models

INSPECTION_RESULTS = [
    ('passed', 'Passed'),
    ('failed', 'Failed'),
]

MEASUREMENT_TYPES = [
    ('spi_paste', 'SPI Solder Paste'),
    ('spi_lean', 'SPI Lean'),
    ('offset', 'Component Offset'),
    ('generic', 'Generic'),
]


class CfxInspectionUnit(models.Model):
    _name = 'cfx.inspection.unit'
    _description = 'CFX Inspected Unit / Panel'
    _order = 'stat_id desc, unit_position'

    stat_id = fields.Many2one(
        'cfx.machine.stat', required=True, ondelete='cascade', index=True)
    # Denormalised за pivot/list филтриране без join.
    machine_kind = fields.Selection(
        related='stat_id.machine_kind', store=True, index=True)
    cfx_handle = fields.Char(related='stat_id.cfx_handle', store=True)
    event_time = fields.Datetime(related='stat_id.event_time', store=True)
    inspection_method = fields.Char(
        related='stat_id.inspection_method', store=True)

    unit_identifier = fields.Char(string='Unit Identifier')
    unit_position = fields.Integer(string='Position')
    overall_result = fields.Selection(INSPECTION_RESULTS, string='Result')
    is_panel = fields.Boolean(string='Panel-level')
    inspection_count = fields.Integer(string='Inspections')
    inspections_passed = fields.Integer(string='Passed')
    inspections_failed = fields.Integer(string='Failed')

    defect_ids = fields.One2many(
        'cfx.inspection.defect', 'unit_id', string='Defects')
    measurement_ids = fields.One2many(
        'cfx.inspection.measurement', 'unit_id', string='Measurements')
    defect_count = fields.Integer(
        compute='_compute_counts', store=True, string='# Defects')
    measurement_count = fields.Integer(
        compute='_compute_counts', store=True, string='# Measurements')

    def _compute_counts(self):
        for rec in self:
            rec.defect_count = len(rec.defect_ids)
            rec.measurement_count = len(rec.measurement_ids)


class CfxInspectionDefect(models.Model):
    _name = 'cfx.inspection.defect'
    _description = 'CFX Inspection Defect'
    _order = 'unit_id desc, priority, id'

    unit_id = fields.Many2one(
        'cfx.inspection.unit', required=True, ondelete='cascade', index=True)
    stat_id = fields.Many2one(
        'cfx.machine.stat', related='unit_id.stat_id',
        store=True, index=True)
    machine_kind = fields.Selection(
        related='stat_id.machine_kind', store=True, index=True)
    cfx_handle = fields.Char(related='stat_id.cfx_handle', store=True)
    event_time = fields.Datetime(related='stat_id.event_time', store=True)
    unit_identifier = fields.Char(
        related='unit_id.unit_identifier', store=True)

    inspection_name = fields.Char(string='Inspection')
    defect_code = fields.Char(string='Defect Code', index=True)
    defect_category = fields.Char(string='Category', index=True)
    description = fields.Char(string='Description')
    reference_designator = fields.Char(string='Reference (CRD)')
    part_number = fields.Char(string='Part Number')
    priority = fields.Integer(string='Priority')
    confidence_level = fields.Float(string='Confidence %')


class CfxInspectionMeasurement(models.Model):
    _name = 'cfx.inspection.measurement'
    _description = 'CFX Inspection Measurement'
    _order = 'unit_id desc, id'

    unit_id = fields.Many2one(
        'cfx.inspection.unit', required=True, ondelete='cascade', index=True)
    stat_id = fields.Many2one(
        'cfx.machine.stat', related='unit_id.stat_id',
        store=True, index=True)
    machine_kind = fields.Selection(
        related='stat_id.machine_kind', store=True, index=True)
    event_time = fields.Datetime(related='stat_id.event_time', store=True)

    inspection_name = fields.Char(string='Inspection')
    meas_type = fields.Selection(MEASUREMENT_TYPES, string='Type')
    measurement_name = fields.Char(string='Measurement')
    crds = fields.Char(string='CRDs')
    result = fields.Selection(INSPECTION_RESULTS, string='Result')
    # Общи числови оси (SPI обем/позиция + AOI отклонение)
    pos_x = fields.Float(string='X')
    pos_y = fields.Float(string='Y')
    pos_z = fields.Float(string='Z')
    dev_x = fields.Float(string='ΔX')
    dev_y = fields.Float(string='ΔY')
    volume = fields.Float(string='Volume')
