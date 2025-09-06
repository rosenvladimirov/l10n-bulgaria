#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BGModEconomicActivity(models.Model):
    _name = 'bg.hr.payroll.economic.activity'
    _description = 'Bulgarian Economic Activity (KID) for MOD'
    _order = 'code'

    name = fields.Char(string='Activity Name', required=True, translate=True)
    code = fields.Char(string='KID Code', required=True, index=True)
    parent_id = fields.Many2one('bg.hr.payroll.economic.activity', string='Parent Activity')
    child_ids = fields.One2many('bg.hr.payroll.economic.activity', 'parent_id', string='Child Activities')
    active = fields.Boolean(string='Active', default=True)
    level = fields.Selection([
        ('section', 'Section'),
        ('division', 'Division'),
        ('group', 'Group'),
        ('class', 'Class')
    ], string='Level', required=True)

    # MOD amounts by qualification groups
    mod_manager = fields.Float(string='MOD - Managers', default=0.0,
                              help='Minimum insurance income for managers')
    mod_specialist = fields.Float(string='MOD - Specialists', default=0.0,
                                 help='Minimum insurance income for specialists')
    mod_technician = fields.Float(string='MOD - Technicians', default=0.0,
                                 help='Minimum insurance income for technicians')
    mod_clerk = fields.Float(string='MOD - Clerks', default=0.0,
                            help='Minimum insurance income for clerks')
    mod_service = fields.Float(string='MOD - Service Workers', default=0.0,
                              help='Minimum insurance income for service workers')
    mod_skilled = fields.Float(string='MOD - Skilled Workers', default=0.0,
                              help='Minimum insurance income for skilled workers')
    mod_operator = fields.Float(string='MOD - Machine Operators', default=0.0,
                               help='Minimum insurance income for machine operators')
    mod_elementary = fields.Float(string='MOD - Elementary Occupations', default=0.0,
                                 help='Minimum insurance income for elementary occupations')

    # TZPB параментри
    tzbp_parameter = fields.Char(string='TZBP Parameter',
                                 help='Work accident and occupational disease insurance parameter')
    tzbp_code = fields.Char(string='TZBP Code', help='TZBP Code')

    # Validity periods
    date_from = fields.Date(string='Valid From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='Valid To')

    @api.depends('code', 'name')
    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override to improve performance when loading large datasets"""
        if not fields:
            fields = ['name', 'code', 'level', 'active']
        return super().search_read(domain, fields, offset, limit, order)

    def get_effective_mod(self, qualification_group):
        """Get effective MOD for a given qualification group"""
        self.ensure_one()
        mapping = {
            'manager': self.mod_manager,
            'specialist': self.mod_specialist,
            'technician': self.mod_technician,
            'clerk': self.mod_clerk,
            'service': self.mod_service,
            'skilled': self.mod_skilled,
            'operator': self.mod_operator,
            'elementary': self.mod_elementary,
        }
        return mapping.get(qualification_group, 0.0)

    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f"KID code '{record.code}' already exists!")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError("Valid From date cannot be after Valid To date!")
