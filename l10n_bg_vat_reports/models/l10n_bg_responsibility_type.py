
from odoo import models, fields


class L10nABGResponsibilityType(models.Model):

    _name = 'l10n_bg.responsibility.type'
    _description = 'Responsibility Type'
    _order = 'sequence'

    name = fields.Char(required=True, index='trigram')
    sequence = fields.Integer()
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]
    
    
    
    # def _prepare_variant_values(self, combination):
    #     variant_dict = super()._prepare_variant_values(combination)
    #     variant_dict["description"] = self.description

    #     # Sort the variant values by name
    #     sorted_variant_values = sorted(variant_dict["value_ids"], key=lambda x: x.name)
    #     variant_dict["value_ids"] = sorted_variant_values

    #     return variant_dict