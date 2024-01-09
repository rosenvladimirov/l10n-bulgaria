#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMoveBgProtocol(models.Model):
    _name = "account.move.bg.protocol"
    _inherits = {'account.move': 'move_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _description = "VAT Protocol for invoice art. 117(2)"
    _order = "date_creation desc, name desc, id desc"
    _mail_post_access = 'read'
    _check_company_auto = True
    _sequence_field = 'l10n_bg_name'

    move_id = fields.Many2one('account.move', string='Account invoice', ondelete="cascade", required=True, index=True)
    date_creation = fields.Date('Created Date', required=True, default=fields.Date.today())

    # -------------------------------------------------------------------------
    # SEQUENCE MIXIN
    # -------------------------------------------------------------------------
    def _get_last_sequence_domain(self, relaxed=False):
        self.ensure_one()
        where_string, param = super()._get_last_sequence_domain(relaxed=relaxed)
        if self.l10n_bg_type_vat == '117_protocol':
            where_string += " AND type_vat = '117_protocol'"
        return where_string, param
