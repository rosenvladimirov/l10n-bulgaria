from odoo import fields, models, api


class NssiLeaveReason(models.Model):
    _name = 'nssi.leave.reason'
    _description = 'NSSI – Leave Reasons (Appendix №9)'
    _order = 'code'

    code = fields.Char(string='Code', size=2, required=True, index=True)
    name = fields.Char(string='Reason', required=True, translate=True)

    _code_uniq = models.Constraint(
        'unique (code)',
        "The code must be unique!",
    )

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        # Odoo 19: BaseModel.name_search преименува args → domain.
        domain = domain or []
        extra_domain = []
        if name:
            extra_domain = ['|', ('code', operator, name), ('name', operator, name)]
        return super().name_search(
            name=name, domain=extra_domain + domain,
            operator=operator, limit=limit,
        )
