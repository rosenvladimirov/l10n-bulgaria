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

    # Override account_rule_ids inherited from l10n.bg.kid (l10n_bg_config 18.0.8.5+):
    # `l10n.bg.kid` declares this Many2many with explicit
    # `relation='l10n_bg_kid_account_rule_rel'`. Because we _inherit l10n.bg.kid as
    # a MIXIN (not _inherits delegation), the field copies into this model's namespace
    # and points to the SAME relation table — but the column1='kid_id' FK then has
    # ambiguous referent (l10n.bg.kid.id vs bg.hr.payroll.economic.activity.id) and
    # Odoo registry setup fails with:
    #     TypeError: Many2many fields ... use the same table and columns
    # Fix: own relation table with explicit FK columns, semantically same semantic
    # ("which account rules apply to this MOD economic-activity sector").
    account_rule_ids = fields.Many2many(
        'l10n.bg.account.kid.rule',
        relation='bg_payroll_eco_activity_kid_rule_rel',
        column1='eco_activity_id',
        column2='rule_id',
        string='Account Rules (MOD)',
        help='Sector-specific account-code rules за този МОД-код. Override '
             'на наследеното от l10n.bg.kid поле с собствена relation table.',
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

    # TZBP-1: ТЗПБ ставката по закон се определя от КИД на дейността
    # (Прил. 2 ЗБДОО), а не от професията (НКПД). Държим я тук, до МОД.
    tzbp_rate = fields.Float(
        string='TZPB Rate',
        default=0.0,
        help='Work-injury and occupational-disease (TZPB) contribution rate '
             'for this economic activity (KID), per Annex 2 of the State Social '
             'Insurance Budget Act. When set (> 0) it takes precedence over the '
             'profession-based (NCOP) rate.',
    )

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

    def get_effective_tzbp_rate(self):
        """Get the effective TZPB rate for this economic activity (КИД).

        The legal TZPB rate is set per economic activity (КИД, Annex 2
        ЗБДОО), not per profession (НКПД).
        """
        self.ensure_one()
        return self.tzbp_rate or 0.0

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError("Valid From date cannot be after Valid To date!")
