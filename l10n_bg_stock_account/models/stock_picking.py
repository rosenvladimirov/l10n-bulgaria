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

    l10n_bg_unvalued_warning = fields.Char(
        compute='_compute_l10n_bg_unvalued_warning',
        string='Valuation Warning',
    )

    @api.depends('move_ids.product_id', 'move_ids.quantity', 'move_ids.value',
                 'state')
    def _compute_l10n_bg_unvalued_warning(self):
        """Предупреждава, че движение ще се осчетоводи (или е осчетоводено) без стойност.

        Преди валидиране гледаме дали продуктът изобщо има от какво да вземе
        себестойност (нормативна цена или заскладена стойност); след
        валидиране — реалната стойност на движението. Без това нулата минава
        мълчаливо: статия не се създава и продажбата остава без себестойност.
        """
        for picking in self:
            products = picking._l10n_bg_unvalued_products()
            if not products:
                picking.l10n_bg_unvalued_warning = False
                continue
            names = ", ".join(products.mapped('display_name')[:5])
            if len(products) > 5:
                names += ", …"
            picking.l10n_bg_unvalued_warning = names

    def _l10n_bg_unvalued_products(self):
        """Продуктите в пикинга, за които няма себестойност."""
        self.ensure_one()
        currency = self.company_id.currency_id or self.env.company.currency_id
        products = self.env['product.product']
        for move in self.move_ids:
            product = move.product_id
            if not product.is_storable or not product.categ_id.sudo().l10n_bg_stock_auto_post:
                continue
            if move.state == 'done':
                if not move.product_uom.is_zero(move.quantity) \
                        and currency.is_zero(move.value):
                    products |= product
                continue
            if move.state in ('draft', 'cancel'):
                continue
            # преди валидиране: има ли изобщо откъде да дойде стойност
            if currency.is_zero(product.standard_price) \
                    and currency.is_zero(product.total_value or 0.0):
                products |= product
        return products

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
