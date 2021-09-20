# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrExpense(models.Model):
    _inherit = "hr.expense"

    narration_id = fields.Many2one('base.comment.template', string='Narration Template')
    doc_justification = fields.Boolean('Documentary justification')
    tax_type_deal = fields.Selection([
        ('auto', _('Automatic discovery')),
        ('entertainment', _('Entertainment expenses')),
        ('social', _('Social expenses provided in kind')),
        ('insurance', _('social expenses for contributions (premiums) for additional social insurance and "Life"')),
        ('voucher', _('The social expenses of food vouchers')),
        ('kind', _('Expenses in kind')),
    ], 'Type deal from taxing view', default='auto',
        help="* The 'Entertainment expenses' is used when this tax is configured to calculate base and amount for 'Tax on entertainment expenses'\n"
             "* The 'Social expenses provided in kind' is used when this tax is configured to calculate base and amount for 'Tax on social expenses provided in kind'\n"
             "* The 'Additional social insurance and Life' is used when this tax is configured to calculate base and amount for 'Tax on social expenses for contributions (premiums) for additional social insurance and Life'\n"
             "* The 'The social expenses of food vouchers' is used when this tax is configured to calculate base and amount for 'Tax on The social expenses of food vouchers'\n"
             "* The 'Expenses in kind' is used when this tax is configured to calculate base and amount for 'Tax on expenses in kind'\n"
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.name:
                self.name = self.product_id.display_name or ''
            self.unit_amount = self.product_id.price_compute('standard_price')[self.product_id.id]
            self.product_uom_id = self.product_id.uom_id
            fpos = self.env.user.company_id.purchase_fp_id
            self.tax_ids = fpos.map_tax(self.product_id.supplier_taxes_id)
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            if account:
                self.account_id = account

    @api.multi
    def _move_line_get(self):
        account_move = []
        for expense in self:
            move_line = expense._prepare_move_line_value()
            account_move.append(move_line)

            # Calculate tax lines and adjust base line
            if not expense.doc_justification:
                tax_ids = expense.tax_ids.filtered(lambda x: x.tax_type_deal).sorted(lambda x: -x.sequence)
            else:
                tax_ids = expense.tax_ids.sorted(lambda x: -x.sequence)
            taxes = tax_ids.with_context(round=True).compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id)
            account_move[-1]['price'] = taxes['total_excluded']
            account_move[-1]['tax_ids'] = [(6, 0, tax_ids.ids)]
            for tax in taxes['taxes']:
                account_move.append({
                    'type': 'tax',
                    'name': tax['name'],
                    'price_unit': tax['amount'],
                    'quantity': 1,
                    'price': tax['amount'],
                    'account_id': tax['account_id'] or move_line['account_id'],
                    'tax_line_id': tax['id'],
                    'expense_id': expense.id,
                })
        return account_move

    def _prepare_move_line(self, line):
        rtrn = super(HrExpense, self)._prepare_move_line(line)
        if self.tax_type_deal != 'auto':
            rtrn.update({
                'tax_type_deal': self.tax_type_deal,
            })
        if self.doc_justification:
            rtrn.update({
                'narration_id': self.narration_id.id,
                'vattype': self.env.ref("l10n_bg.vattype_03_09").id,
                'doc_justification': self.doc_justification,
            })
        return rtrn
