#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BGNCOPClassification(models.Model):
    _name = 'bg.hr.payroll.ncop.classification'
    _description = 'Bulgarian NCOP Classification 2011'
    _order = 'code'
    # Търсене по КОД и по име (НКПД има 6107 позиции — ползвачите търсят по код).
    # Стандартният name_search гледа само _rec_name (name) → 0 резултата за код.
    _rec_names_search = ['code', 'name']

    name = fields.Char(string='Position Name', required=True, translate=True)
    code = fields.Char(string='NCOP Code', required=True, index=True,
                       help='8-digit NCOP code')
    parent_id = fields.Many2one('bg.hr.payroll.ncop.classification', string='Parent Position')
    child_ids = fields.One2many('bg.hr.payroll.ncop.classification', 'parent_id', string='Child Positions')
    active = fields.Boolean(string='Active', default=True)

    level = fields.Selection([
        ('major_group', 'Major Group'),
        ('sub_major_group', 'Sub-Major Group'),
        ('minor_group', 'Minor Group'),
        ('unit_group', 'Unit Group'),
        ('occupation', 'Occupation')
    ], string='Level', required=True,
        help='Hierarchical level in NCOP structure')

    # Qualification group mapping for MOD calculation
    qualification_group = fields.Selection([
        ('military', 'Military'),
        ('manager', 'Managers'),
        ('specialist', 'Specialists'),
        ('technician', 'Technicians'),
        ('clerk', 'Clerks'),
        ('service', 'Service Workers'),
        ('skilled', 'Skilled Workers'),
        ('operator', 'Machine Operators'),
        ('elementary', 'Elementary Occupations')
    ], string='Qualification Group',
        help='Qualification group for MOD calculation based on NCOP class')

    # Required education level
    education_level = fields.Selection([
        ('none', 'No formal education'),
        ('primary', 'Primary education'),
        ('secondary', 'Secondary education'),
        ('higher', 'Higher education')
    ], string='Education Level',
        help='Minimum required education level for this position')

    # Skills and experience requirements
    skill_level = fields.Integer(
        string='Skill Level',
        help='Skill level (1-4) according to NCOP classification'
    )

    skills_requirements = fields.Text(string='Skills Requirements')
    experience_years = fields.Integer(string='Required Experience (years)', default=0)

    # Validity period
    date_from = fields.Date(string='Valid From', default=fields.Date.today)
    date_to = fields.Date(string='Valid To')

    @api.depends('code', 'name')
    def _compute_display_name(self):
        """Override display name computation for Odoo 19"""
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"

    @api.onchange('code')
    def _onchange_code_set_qualification_group(self):
        """Auto-set qualification group based on NKPD class (first digit)"""
        if self.code and len(self.code) >= 1:
            class_digit = self.code[0]
            mapping = {
                '0': 'military',  # Клас 0 - Професии във въоръжените сили
                '1': 'manager',  # Клас 1 - Ръководители
                '2': 'specialist',  # Клас 2 - Специалисти
                '3': 'technician',  # Клас 3 - Техници
                '4': 'clerk',  # Клас 4 - Помощен административен персонал
                '5': 'service',  # Клас 5 - Работници, заети с услуги
                '6': 'skilled',  # Клас 6 - Квалифицирани работници в селското стопанство
                '7': 'skilled',  # Клас 7 - Квалифицирани работници и занаятчии
                '8': 'operator',  # Клас 8 - Машинисти и оператори
                '9': 'elementary'  # Клас 9 - Професии, неизискващи квалификация
            }
            self.qualification_group = mapping.get(class_digit)

    @api.onchange('code')
    def _onchange_code_set_level(self):
        """Auto-determine level based on code length and content"""
        if self.code:
            code_len = len(self.code)
            if code_len == 1:
                self.level = 'major_group'  # Основна група (клас)
            elif code_len == 2:
                self.level = 'sub_major_group'  # Подгрупа
            elif code_len == 3:
                self.level = 'minor_group'  # Малка grupa
            elif code_len == 4:
                self.level = 'unit_group'  # Единична група
            elif code_len >= 5:
                self.level = 'occupation'  # Конкретна професия

    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f"NCOP code '{record.code}' already exists!")

    @api.constrains('code')
    def _check_code_format(self):
        for record in self:
            if not record.code.isdigit():
                raise ValidationError("NCOP code must contain only digits!")
            if len(record.code) < 1 or len(record.code) > 8:
                raise ValidationError("NCOP code must be between 1 and 8 digits long!")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError("Valid From date cannot be after Valid To date!")

    def get_qualification_mapping(self):
        """Get qualification group for MOD calculation"""
        self.ensure_one()
        return self.qualification_group or 'elementary'

    def get_hierarchy_path(self):
        """Get a full hierarchical path from class to this position"""
        self.ensure_one()
        path = []
        current = self
        while current:
            path.insert(0, current)
            current = current.parent_id
        return path

    @api.model
    def search_positions_by_name(self, name_part):
        """Search positions by partial name match"""
        return self.search([
            ('name', 'ilike', name_part),
            ('active', '=', True)
        ])

    @api.model
    def get_positions_by_qualification_group(self, qualification_group):
        """Get all positions for a specific qualification group"""
        return self.search([
            ('qualification_group', '=', qualification_group),
            ('active', '=', True)
        ])
