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

        # Трябва да е storable + valued + incoming или outgoing
        return (
            self.product_id.is_storable
            and self.is_valued
            and (self.is_in or self.is_dropship or self.is_out)
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

        if not stock_valuation_acc:
            return []

        value = abs(self.value)
        categ = self.product_id.categ_id.sudo()

        # Изходящ move: Dr. output_account (702.100) / Cr. stock_valuation (302)
        if self.is_out:
            output_acc = categ.l10n_bg_stock_output_account_id
            if not output_acc:
                return []
            return [
                {
                    'account_id': output_acc.id,
                    'name': self.reference,
                    'debit': value,
                    'credit': 0.0,
                    'product_id': self.product_id.id,
                },
                {
                    'account_id': stock_valuation_acc.id,
                    'name': self.reference,
                    'debit': 0.0,
                    'credit': value,
                    'product_id': self.product_id.id,
                },
            ]

        # Входящ move: Dr. stock_valuation (302) / Cr. input_account (301)
        # Fallback към stock_variation ако input_account не е зададен
        input_acc = categ.l10n_bg_stock_input_account_id or accounts.get('stock_variation')
        if not input_acc:
            return []

        return [
            # Credit: transit / GRNI (input account — 301)
            {
                'account_id': input_acc.id,
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
