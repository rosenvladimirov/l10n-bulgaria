# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class StockLocation(models.Model):
    _inherit = "stock.location"

    second_valuation_in_account_id = fields.Many2one(
        'account.account', 'Stock BG Valuation Account (Incoming)',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Used for real-time inventory transit distinction e.g 611."
             " When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved from an internal location "
             "into this location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def _get_accounting_data_for_valuation(self):
        self.ensure_one()
        journal_id, acc_src, acc_dest, acc_valuation = super(StockMove, self)._get_accounting_data_for_valuation()
        if self._context.get('account_transit', False):
            if self.location_dest_id.second_valuation_in_account_id:
                acc_src = self.location_dest_id.valuation_in_account_id.id
                acc_dest = self.location_dest_id.second_valuation_in_account_id.id
        return journal_id, acc_src, acc_dest, acc_valuation

    @api.multi
    def _account_entry_move(self):
        self.ensure_one()
        super(StockMove, self)._account_entry_move()

        if self.raw_material_production_id:
            company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False
            journal_id, acc_src, acc_dest, acc_valuation = self.\
                with_context(dict(self._context, account_transit=True))._get_accounting_data_for_valuation()
            self.with_context(force_company=company_to.id).\
                _create_account_move_line(acc_src, acc_valuation, journal_id)
