# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _

import logging
_logger = logging.getLogger(__name__)


class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    info = fields.Text("Description")
    type_accounts = fields.Selection([
                            ('0',_('Balance Debit')),
                            ('1',_('Balance Credit')),
                            ('2',_('Movements Debit')),
                            ('3',_('Movements Credit')),
                            ('4',_('Correspondence from General Ledger')),
                            ('9',_('Empty'))
                            ], string="Get from", size=1, readonly=False)

#    display_name = fields.Char(compute='_compute_display_name')

#    @api.depends('name', 'code')
#    def _compute_display_name(self):
#        for tag in self:
#            if self._context.get('only_code'):
#                tag.display_name = "%s" % tag.code
#            if tag.code and tag.name:
#                tag.display_name = "[%s] %s" % (tag.code, tag.name)
#            elif tag.code and not tag.name:
#                tag.display_name = "%s" % tag.code
#            elif tag.name and not tag.code:
#                tag.display_name = "%s" % tag.code
#            else:
#                tag.display_name = "%s" % tag.code


class AccountTax(models.Model):
    _inherit = 'account.tax'

    tax_credit_payable = fields.Selection([('taxcredit', 'Tax credit receivable from the taxpayer'),
                                           ('taxpay', 'Tax payable by the taxpayer'),
                                           ('eutaxcredit', 'Tax credit receivable from the taxpayer on EU deals'),
                                           ('eutaxpay', 'Tax payable by the taxpayer on EU deals'),
                                           ('taxadvpay', 'Tax payable by the taxpayer when Imports from outside EU'),
                                           ('taxbalance', 'Account for balance of taxes'),
                                           ('othertax', 'Different by VAT Tax payable by the taxpayer')],
                                          'Who pays tax', required=False, default='taxpay',
                                          help="If not applicable (computed through a Python code), the tax won't "
                                               "appear on the invoice.Who pays the tax purchaser or seller ( for "
                                               "imports from outside the EU pay the buyer )")
    separate = fields.Boolean('Separate movement')
    contrapart_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)],
                                            string='Contrapart Account', ondelete='restrict',
                                            help="Account that will be set when work with separated movement for "
                                                 "contra part. Leave empty to use the contrapart account.")
    parent_tax_ids = fields.Many2many('account.tax', 'account_tax_filiation_rel', 'child_tax', 'parent_tax',
                                      string='Parent Taxes')

    # Maybe in future change with account tax type
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

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        ret = super(AccountTax, self)._compute_amount(base_amount, price_unit, quantity=quantity, product=product,
                                                      partner=partner)
        koef = 1.0
        # _logger.info("Taxes %s:%s:%s" % (self.name, self.tax_credit_payable, self.type_tax_use))
        if self.type_tax_use == 'none' and self.tax_credit_payable in ('taxpay', 'eutaxpay'):
            koef = -1.0
            ret = abs(ret)
        return ret * koef


# moved from l10n_bg_account_types
class AccountAccountType(models.Model):
    _inherit = "account.account.type"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _rec_name = 'complete_name'
    _order = 'parent_left'

    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True, translate=True)
    display_name = fields.Char(compute='_compute_display_name')
    internal_group = fields.Selection([
        ('equity', 'Equity'),
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('off_balance', 'Off Balance'),
    ], string="Internal Group",
        required=True,
        help="The 'Internal Group' is used to filter accounts based on the internal group set on the account type.")
    journal_type = fields.Selection([
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'Miscellaneous'),], string="Journal type")
    balance = fields.Selection([('debit', 'Debit'), ('credit', 'Credit'),], string="Used type balance")

    parent_id = fields.Many2one('account.account.type', 'Parent Type', index=True, ondelete='cascade')
    child_id = fields.One2many('account.account.type', 'parent_id', 'Child Types')
    parent_left = fields.Integer('Left Parent', index=1)
    parent_right = fields.Integer('Right Parent', index=1)
    top_parent_id = fields.Many2one('account.account.type', 'Top level parent', compute="_compute_top_parent_id")

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for type in self:
            if type.parent_id:
                type.complete_name = '%s / %s' % (type.parent_id.complete_name, type.name)
            else:
                type.complete_name = type.name

    def _compute_top_parent_id(self):
        for type in self:
            top_parent_id = type
            while top_parent_id.parent_id:
                top_parent_id = top_parent_id.parent_id
            _logger.info("TOP LEVEL %s" % top_parent_id)
            type.top_parent_id = top_parent_id.id

    def _compute_display_name(self):
        for type in self:
            type.display_name = type.complete_name


# moved from l10n_bg_account_types
class AccountAccount(models.Model):
    _inherit = "account.account"

    internal_group = fields.Selection(related='user_type_id.internal_group', string="Internal Group", store=True,
                                      readonly=True)
    journal_type = fields.Selection(related='user_type_id.journal_type', string="Journal Type", store=True,
                                    readonly=True)
    parent_user_type_id = fields.Many2one('account.account.type', string='Top Level Type', store=True, readonly=True)
    allowed_journal_ids = fields.Many2many('account.journal', string="Allowed Journals", help="Define in which "
                                                                                              "journals this account "
                                                                                              "can be used. If empty, "
                                                                                              "can be used in all "
                                                                                              "journals.")
    clear_balance = fields.Boolean()
