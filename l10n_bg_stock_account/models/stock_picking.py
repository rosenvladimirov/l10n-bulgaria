from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_bg_account_move_ids = fields.Many2many(
        'account.move',
        compute='_compute_l10n_bg_account_move_ids',
        string='Journal Entries',
    )
    l10n_bg_account_move_count = fields.Integer(
        compute='_compute_l10n_bg_account_move_ids',
        string='Journal Entries',
    )

    @api.depends('move_ids.account_move_id')
    def _compute_l10n_bg_account_move_ids(self):
        for picking in self:
            moves = picking.move_ids.mapped('account_move_id').filtered(bool)
            picking.l10n_bg_account_move_ids = moves
            picking.l10n_bg_account_move_count = len(moves)

    def l10n_bg_action_view_account_moves(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.l10n_bg_account_move_ids.ids)],
        }
        if self.l10n_bg_account_move_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.l10n_bg_account_move_ids.id
        else:
            action['view_mode'] = 'list,form'
        return action
