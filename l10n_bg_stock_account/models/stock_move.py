from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _should_create_account_move(self):
        """Разширява стандартното условие: ако категорията има l10n_bg_stock_auto_post=True,
        се позволява генериране на счетоводен запис при incoming пикинг дори при manual_periodic.

        Стандартното условие изисква valuation == 'real_time'. Ние го заобикаляме само за
        incoming moves (is_in или is_dropship) с auto_post категория.
        """
        self.ensure_one()
        # Стандартна проверка — real_time продуктите минават по нормалния път
        if super()._should_create_account_move():
            return True

        # BG auto-post: само за incoming moves на storable продукти с auto_post категория
        categ = self.product_id.categ_id.sudo()
        if not categ.l10n_bg_stock_auto_post:
            return False

        # Трябва да е storable + valued + incoming (receipt или dropship)
        return (
            self.product_id.is_storable
            and self.is_valued
            and (self.is_in or self.is_dropship)
        )

    def _get_account_move_line_vals(self):
        """За auto_post категории: генерира стандартната BG складова статия.

        Dr. property_stock_valuation_account_id  (стойност на стоката)
        Cr. account_stock_variation_id            (GRNI / clearing сметка)

        При real_time продукти делегира към стандартния метод (location-based).
        """
        self.ensure_one()

        # Стандартен path за real_time продукти
        if self.product_id.valuation == 'real_time':
            return super()._get_account_move_line_vals()

        # BG auto-post path
        categ = self.product_id.categ_id.sudo()
        if not categ.l10n_bg_stock_auto_post:
            return super()._get_account_move_line_vals()

        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        stock_valuation_acc = accounts.get('stock_valuation')
        stock_variation_acc = accounts.get('stock_variation')

        if not stock_valuation_acc:
            return []

        # Ако няма variation account (GRNI), не можем да балансираме — skip
        if not stock_variation_acc:
            return []

        value = abs(self.value)
        return [
            # Credit: GRNI / clearing (stock variation account)
            {
                'account_id': stock_variation_acc.id,
                'name': self.reference,
                'debit': 0.0,
                'credit': value,
                'product_id': self.product_id.id,
            },
            # Debit: Stock valuation account (302/303/304)
            {
                'account_id': stock_valuation_acc.id,
                'name': self.reference,
                'debit': value,
                'credit': 0.0,
                'product_id': self.product_id.id,
            },
        ]
