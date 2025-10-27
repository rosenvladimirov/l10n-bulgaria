from odoo import api, fields, models, _


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    l10n_bg_fiscal_tax_group = fields.Selection([
        ('А', 'A - VAT 0%'),
        ('Б', 'B - VAT 20%'),
        ('В', 'C - VAT 20%'),
        ('Г', 'D - VAT 9%')
    ], string='Tax group', default='Б',
       help='Tax group for a fiscal printer')

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'BG':
            return res + ['l10n_bg_fiscal_tax_group']
        return res
