# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    separate = fields.Boolean('Separate movement')
    eu_deals = fields.Boolean('The intra-Community supply tax is chargeable')
    doc_justification = fields.Boolean('Documentary justification')
    tax_type_deal = fields.Selection([
            ('auto', _('Automatic discovery')),
            ('standard', _('Product direct selling')),
            ('service', _('Service direct selling')),
            ('ptriangles', _('Product triangles deals')),
            ('striangles', _('Service triangles deals')),
            ('entertainment', _('Entertainment expenses')),
            ('social', _('Social expenses provided in kind')),
            ('insurance', _('social expenses for contributions (premiums) for additional social insurance and "Life"')),
            ('voucher', _('The social expenses of food vouchers')),
            ('kind', _('Expenses in kind')),
        ], 'Type deal from taxing view',
        help="* The 'Automatic discovery' is used when do not have special tax for other types of the 'Type deal'.\n"
             "* The 'Product direct selling' is used when this tax is configured for standard deal only with products.\n"
             "* The 'Service direct selling' is used when this tax is configured for standard deal only with services.\n"
             "* The 'Product triangles deals' is used when this tax is configured for triangles deal only with products.\n"
             "* The 'Service triangles deals' is used when this tax is configured for triangles deal only with services.\n"
             "* The 'Entertainment expenses' is used when this tax is configured to calculate base and amount for 'Tax on entertainment expenses'\n"
             "* The 'Social expenses provided in kind' is used when this tax is configured to calculate base and amount for 'Tax on social expenses provided in kind'\n"
             "* The 'Additional social insurance and Life' is used when this tax is configured to calculate base and amount for 'Tax on social expenses for contributions (premiums) for additional social insurance and Life'\n"
             "* The 'The social expenses of food vouchers' is used when this tax is configured to calculate base and amount for 'Tax on The social expenses of food vouchers'\n"
             "* The 'Expenses in kind' is used when this tax is configured to calculate base and amount for 'Tax on expenses in kind'\n"
        )
