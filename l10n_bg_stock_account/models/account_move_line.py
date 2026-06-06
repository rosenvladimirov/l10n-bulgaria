from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_account_id(self):
        """За auto_post продукти при vendor bill: задава stock_variation account
        вместо expense account.

        Стандартното поведение (stock_account): при real_time задава stock_valuation account.
        Нашият случай: при auto_post periodic задаваме stock_variation (GRNI/clearing),
        за да може при фактуриране разликата от clearing-а да се изравни коректно.

        Сценарий:
          - При пикинг: Dr. 302, Cr. stock_variation (GRNI)
          - При фактура: Dr. stock_variation (GRNI), Cr. 401 (AP) — стандартен ред от нашия override
          - Разликата PO↔Invoice се обработва от l10n_bg_stock_price_diff
        """
        super()._compute_account_id()
        for line in self:
            if not line.move_id.is_purchase_document():
                continue
            if line.display_type != 'product':
                continue
            if not line.product_id.is_storable:
                continue
            categ = line.product_id.categ_id.sudo()
            if not categ.l10n_bg_stock_auto_post:
                continue
            # Само за periodic (real_time вече е обработено от super())
            if line.product_id.valuation == 'real_time':
                continue

            accounts = line.with_company(line.company_id).product_id.product_tmpl_id.get_product_accounts(
                fiscal_pos=line.move_id.fiscal_position_id
            )
            categ = line.product_id.categ_id.sudo()
            # Ползваме input account (301) ако е зададен, иначе fallback към stock_variation (409)
            transit_acc = categ.l10n_bg_stock_input_account_id or accounts.get('stock_variation')
            if transit_acc:
                line.account_id = transit_acc
