#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BGModEconomicActivity(models.Model):
    """Bulgarian Economic Activity (КИД) for MOD.

    The neutral КИД structure (code / name / level / parent / version /
    industry bridge) now lives canonically in ``l10n.bg.kid``
    (``l10n_bg_config``). This model keeps its own table, name, data,
    ids, views and dependents *unchanged* — it merely prototype-inherits
    the shared definition and adds the payroll-only MOD amounts. The
    self-referential hierarchy fields are re-targeted to this model so
    the existing seed (``parent_id/id``) and views keep working as-is;
    the upgrade only adds two nullable columns (``kid_version``,
    ``partner_industry_id``) and needs no data migration.
    """

    _name = 'bg.hr.payroll.economic.activity'
    _inherit = ['l10n.bg.kid']
    _description = 'Bulgarian Economic Activity (KID) for MOD'
    _order = 'code'

    # Keep the hierarchy inside this model (do not delegate to l10n.bg.kid)
    # so the pre-existing seed / views / dependents stay byte-compatible.
    parent_id = fields.Many2one(
        'bg.hr.payroll.economic.activity', string='Parent Activity'
    )
    child_ids = fields.One2many(
        'bg.hr.payroll.economic.activity', 'parent_id', string='Child Activities'
    )

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

    # Validity periods
    date_from = fields.Date(string='Valid From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='Valid To')

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

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError("Valid From date cannot be after Valid To date!")
