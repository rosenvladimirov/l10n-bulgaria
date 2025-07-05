from odoo import models, fields, api, _


class ProductCategory(models.Model):
    _inherit = 'product.category'

    fiscal_tax_group = fields.Selection([
        ('А', 'A - VAT 0%'),
        ('Б', 'B - VAT 20%'),
        ('В', 'C - VAT 20%'),
        ('Г', 'D - VAT 9%')
    ], string='Tax group', default='Б',
       help='Tax group for a fiscal printer')

    def get_fiscal_tax_group(self):
        """Рекурсивно търсене на данъчна група в родителските категории"""
        category = self
        while category:
            if category.fiscal_tax_group:
                return category.fiscal_tax_group
            category = category.parent_id
        return 'Б'
