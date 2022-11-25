# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields

import logging
_logger = logging.getLogger(__name__)


class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    info = fields.Text("Description")
    type_accounts = fields.Selection([
                            ('0', 'Balance Debit'),
                            ('1', 'Balance Credit'),
                            ('2', 'Movements Debit'),
                            ('3', 'Movements Credit'),
                            ('4', 'Correspondence from General Ledger'),
                            ('9', 'Empty')
                            ], string="Get from", size=1, readonly=False)
    applicability = fields.Selection(selection_add=[('social', 'Social security payments')])


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
