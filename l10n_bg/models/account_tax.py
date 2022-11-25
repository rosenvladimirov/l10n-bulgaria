# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account.models.account_tax import AccountTax as accounttax, TYPE_TAX_USE

import math
import logging


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def get_virtual_amount(self):
        return self.virtual_amount_ids and self.virtual_amount_ids[-1] or self.amount

    def set_virtual_amount(self, old_value):
        if self.virtual_amount_ids.filtered(lambda r: r.virtual_amount == old_value):
            return False
        return {
            'virtual_amount': old_value,
        }

    def _set_virtual_amount(self):
        for record in self:
            value = record.set_virtual_amount(record.virtual_amount)
            if value:
                record.update({
                    'virtual_amount_ids': [(0, False, value)]
                })

    def _get_virtual_amount(self):
        for record in self:
            record.virtual_amount = record.get_virtual_amount()

    virtual_amount = fields.Float(compute='_get_virtual_amount', inverse='_set_virtual_amount',
                                  digits=(16, 4), default=0.0)
    virtual_amount_ids = fields.One2many('account.tax.virtual.value', 'tax_id', string='Tax virtual line',
                                         copy=True, auto_join=True)
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
             "* The 'Product direct selling' is used when this tax is configured for standard deal only with "
             "products.\n "
             "* The 'Service direct selling' is used when this tax is configured for standard deal only with "
             "services.\n "
             "* The 'Product triangles deals' is used when this tax is configured for triangles deal only with "
             "products.\n "
             "* The 'Service triangles deals' is used when this tax is configured for triangles deal only with "
             "services.\n "
             "* The 'Entertainment expenses' is used when this tax is configured to calculate base and amount for "
             "'Tax on entertainment expenses'\n "
             "* The 'Social expenses provided in kind' is used when this tax is configured to calculate base and "
             "amount for 'Tax on social expenses provided in kind'\n "
             "* The 'Additional social insurance and Life' is used when this tax is configured to calculate base and "
             "amount for 'Tax on social expenses for contributions (premiums) for additional social insurance and "
             "Life'\n "
             "* The 'The social expenses of food vouchers' is used when this tax is configured to calculate base and "
             "amount for 'Tax on The social expenses of food vouchers'\n "
             "* The 'Expenses in kind' is used when this tax is configured to calculate base and amount for 'Tax on "
             "expenses in kind'\n "
    )

    # def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
    #     ret = super(AccountTax, self)._compute_amount(base_amount, price_unit, quantity=quantity, product=product,
    #                                                   partner=partner)
    #     koef = 1.0
    #     if self.type_tax_use == 'none' and self.tax_credit_payable in ('taxpay', 'eutaxpay'):
    #         koef = -1.0
    #         ret = abs(ret)
    #     return ret * koef

    def get_amount(self):
        return self.get_virtual_amount()

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        self.ensure_one()
        amount = self.get_amount()

        if self.amount_type == 'fixed':
            # Use copysign to take into account the sign of the base amount which includes the sign
            # of the quantity and the sign of the price_unit
            # Amount is the fixed price for the tax, it can be negative
            # Base amount included the sign of the quantity and the sign of the unit price and when
            # a product is returned, it can be done either by changing the sign of quantity or by changing the
            # sign of the price unit.
            # When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
            # a "else" case is needed.
            if base_amount:
                return math.copysign(quantity, base_amount) * amount
            else:
                return quantity * amount

        price_include = self._context.get('force_price_include', self.price_include)

        # base * (1 + tax_amount) = new_base
        if self.amount_type == 'percent' and not price_include:
            return base_amount * amount / 100
        # <=> new_base = base / (1 + tax_amount)
        if self.amount_type == 'percent' and price_include:
            return base_amount - (base_amount / (1 + amount / 100))
        # base / (1 - tax_amount) = new_base
        if self.amount_type == 'division' and not price_include:
            return base_amount / (1 - amount / 100) - base_amount if (1 - amount / 100) else 0.0
        # <=> new_base * (1 - tax_amount) = base
        if self.amount_type == 'division' and price_include:
            return base_amount - (base_amount * (amount / 100))
        # default value for custom amount_type
        return 0.0


accounttax._compute_amount = AccountTax._compute_amount


class AccountTaxVirtualValue(models.Model):
    _name = 'account.tax.virtual.value'
    _description = 'Tax'
    _order = 'tax_id, sequence,id'
    _check_company_auto = True

    tax_id = fields.Many2one('account.tax', string='Tax', required=True, ondelete='cascade', index=True, copy=False)
    sequence = fields.Integer(required=True, default=1,
                              help="The sequence field is used to define order in which the virtual values are applied.")
    virtual_amount = fields.Float(required=True, digits=(16, 4), default=0.0)
