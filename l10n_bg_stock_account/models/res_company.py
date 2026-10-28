"""Приключването при periodic не бива да рекласифицира auto_post движенията.

Ядрото (``stock_account``, ``_get_location_valuation_vals``) при приключване
прехвърля стойността на всички periodic движения към/от виртуална локация със
сметка: Дт сметката на локацията / Кт склада (и обратно). Филтърът му не гледа
``account_move_id``. Движение, осчетоводено веднага от ``l10n_bg_stock_auto_post``
(вече Дт сметката на локацията / Кт склада), влиза втори път — разходът се
надува, а балансирането на склада после кредитира сметката за вариации със
същата сума.

Методът повтаря логиката на ядрото (19.0) с едно допълнение:
``('account_move_id', '=', False)`` в базовия домейн на движенията. При
промяна в ядрото — сверявай с ``stock_account/models/res_company.py``.
"""
from collections import defaultdict

from odoo import _, models
from odoo.fields import Domain


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_location_valuation_vals(self, at_date=None, location_domain=False):
        location_domain = Domain.AND([
            location_domain or [],
            [('valuation_account_id', '!=', False)],
            [('company_id', '=', self.id)],
        ])
        amls_vals_list = []
        valued_location = self.env['stock.location'].search(location_domain)
        last_closing_date = self._get_last_closing_date()
        moves_base_domain = Domain([
            ('product_id.is_storable', '=', True),
            ('product_id.valuation', '=', 'periodic'),
            # вече осчетоводените (auto_post) не се рекласифицират втори път
            ('account_move_id', '=', False),
        ])
        if last_closing_date:
            moves_base_domain &= Domain([('date', '>', last_closing_date)])
        if at_date:
            moves_base_domain &= Domain([('date', '<=', at_date)])
        moves_in_domain = Domain([
            ('is_out', '=', True),
            ('company_id', '=', self.id),
            ('location_dest_id', 'in', valued_location.ids),
        ]) & moves_base_domain
        moves_in_by_location = self.env['stock.move']._read_group(
            moves_in_domain,
            ['location_dest_id', 'product_category_id'],
            ['value:sum'],
        )
        moves_out_domain = Domain([
            ('is_in', '=', True),
            ('company_id', '=', self.id),
            ('location_id', 'in', valued_location.ids),
        ]) & moves_base_domain
        moves_out_by_location = self.env['stock.move']._read_group(
            moves_out_domain,
            ['location_id', 'product_category_id'],
            ['value:sum'],
        )
        account_balance = defaultdict(float)
        for location, category, value in moves_in_by_location:
            stock_valuation_acc = (
                category.property_stock_valuation_account_id
                or self.account_stock_valuation_id
            )
            account_balance[location.valuation_account_id, stock_valuation_acc] += value

        for location, category, value in moves_out_by_location:
            stock_valuation_acc = (
                category.property_stock_valuation_account_id
                or self.account_stock_valuation_id
            )
            account_balance[location.valuation_account_id, stock_valuation_acc] -= value

        for (location_account, stock_account), balance in account_balance.items():
            if balance == 0:
                continue
            amls_vals = self._prepare_inventory_aml_vals(
                location_account,
                stock_account,
                balance,
                _('Closing: Location Reclassification - [%(account)s]',
                  account=location_account.display_name),
            )
            amls_vals_list += amls_vals
        return amls_vals_list
