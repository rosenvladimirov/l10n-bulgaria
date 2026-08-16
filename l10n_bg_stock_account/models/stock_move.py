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

        При real_time продукти делегира към стандартния метод (location-based)
        с една BG корекция: при scrap подменяме COGS със loss account от
        product.category.l10n_bg_stock_loss_account_id, ако е настроен.
        """
        self.ensure_one()

        # Производствени движения (консумация в / получаване от производствена
        # локация) се осчетоводяват по стандартния Odoo 19 location-based
        # механизъм — през сметката на производствената локация (Cost of
        # Production), а НЕ през продажбената category output/input сметка
        # (напр. 709.200 'отчетна стойност на продадени материали', която е
        # за реализация, не за влагане). Така вложените в производство
        # материали отиват в производствената сметка и се позволява
        # надграждане от l10n_bg_mrp_account (транзит 601 → 611).
        if (
            self.location_id.usage == 'production'
            or self.location_dest_id.usage == 'production'
        ):
            return super()._get_account_move_line_vals()

        # Стандартен path за real_time продукти + BG scrap корекция
        if self.product_id.valuation == 'real_time':
            vals = super()._get_account_move_line_vals()
            if self.scrap_id and self.is_out:
                vals = self._l10n_bg_substitute_scrap_account(vals)
            return vals

        # BG auto-post path
        categ = self.product_id.categ_id.sudo()
        if not categ.l10n_bg_stock_auto_post:
            vals = super()._get_account_move_line_vals()
            if self.scrap_id and self.is_out:
                vals = self._l10n_bg_substitute_scrap_account(vals)
            return vals

        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        stock_valuation_acc = accounts.get('stock_valuation')

        if not stock_valuation_acc:
            return []

        value = abs(self.value)
        categ = self.product_id.categ_id.sudo()

        # Scrap или негативна inventory adjustment → loss account (669.xxx) вместо COGS.
        # Без отделна сметка системата (стандартно) ползваше l10n_bg_stock_output (COGS) —
        # счетоводно грешно, защото брак не е реализирана продажба.
        is_loss = bool(self.scrap_id) or (self.is_inventory and self.is_out)

        # Изходящ move: Dr. output_account (702.100) / Cr. stock_valuation (302)
        # При scrap/loss → Dr. loss_account (669.xxx) с fallback към output_account.
        if self.is_out:
            output_acc = (
                categ.l10n_bg_stock_loss_account_id
                if is_loss
                else False
            ) or categ.l10n_bg_stock_output_account_id
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
        # При положителна inventory adjustment → Cr. gain_account (709.xxx)
        # с fallback към input_account → stock_variation.
        is_gain = self.is_inventory and self.is_in
        input_acc = (
            (categ.l10n_bg_stock_gain_account_id if is_gain else False)
            or categ.l10n_bg_stock_input_account_id
            or accounts.get('stock_variation')
        )
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

    def _l10n_bg_substitute_scrap_account(self, vals):
        """Замени COGS account със loss account при scrap.

        Стандартното Odoo поведение при scrap е да дебитира output account
        (typically 701.100 — себестойност продадена продукция), което
        счетоводно е грешно — брак не е реализирана продажба.

        Когато категорията има ``l10n_bg_stock_loss_account_id``
        (типично 669.200 — извънредни разходи / брак), подменяме
        debit account-а на стандартния move с loss account-а.
        """
        self.ensure_one()
        loss_acc = self.product_id.categ_id.sudo().l10n_bg_stock_loss_account_id
        if not loss_acc or not vals:
            return vals
        for line in vals:
            # При is_out: debit на изходящ е COGS/output. Cr. остава на
            # stock valuation. Подменяме само debit-а.
            if line.get('debit', 0.0) > 0 and line.get('credit', 0.0) == 0.0:
                line['account_id'] = loss_acc.id
        return vals
