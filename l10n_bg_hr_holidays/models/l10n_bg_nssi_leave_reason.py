from odoo import fields, models, api


class NssiLeaveReason(models.Model):
    _name = 'nssi.leave.reason'
    _description = 'NSSI – Leave Reasons (Appendix №9)'
    _order = 'code'

    code = fields.Char(string='Code', size=2, required=True, index=True)
    name = fields.Char(string='Reason', required=True, translate=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The code must be unique.'),
    ]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        return super().name_search(name=name, args=domain+args, operator=operator, limit=limit)
