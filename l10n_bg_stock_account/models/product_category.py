from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    # Транзитна сметка (напр. 301) — кредитира се при приход на стоката.
    # Dr. stock_valuation (302) / Cr. l10n_bg_stock_input_account_id (301)
    # При отсъствие се ползва account_stock_variation_id.
    l10n_bg_stock_input_account_id = fields.Many2one(
        'account.account',
        string='Stock Input Account',
        company_dependent=True,
        check_company=True,
        help='Transit account credited when goods are received (e.g. 301). '
             'Debited when vendor bill is posted. '
             'Falls back to Stock Variation Account if not set.',
    )

    # Сметка за изписване/COGS (напр. 702.100) — дебитира се при изходящ move.
    # Dr. l10n_bg_stock_output_account_id (702.100) / Cr. stock_valuation (302)
    l10n_bg_stock_output_account_id = fields.Many2one(
        'account.account',
        string='Stock Output Account',
        company_dependent=True,
        check_company=True,
        help='COGS/expense account debited when goods are issued (e.g. 702.100).',
    )

    # Флаг за автоматично счетоводство при валидация на пикинг.
    # Позволява manual_periodic продукти да генерират счетоводни записи при PO цена,
    # без да се сменя property_valuation на 'real_time'.
    l10n_bg_stock_auto_post = fields.Boolean(
        string='Auto-post stock accounting on validate',
        company_dependent=True,
        help='When enabled, a journal entry is created automatically when a receipt is '
             'validated (for manual/periodic costing products). The entry debits the '
             'stock valuation account and credits the stock variation (GRNI) account.',
    )

    # Сметка за ценова разлика (+): clearing при invoice > PO.
    # Използва се от l10n_bg_stock_price_diff за контра в инвойса.
    l10n_bg_price_diff_account_id = fields.Many2one(
        'account.account',
        string='Price Difference Account (+)',
        company_dependent=True,
        check_company=True,
        help='Clearing account used when the vendor invoice price is higher than the PO price. '
             'The price difference module (l10n_bg_stock_price_diff) will clear this account '
             'by distributing the difference through the production chain.',
    )

    # Сметка за приход от ценова разлика (−): директен финансов приход при invoice < PO.
    l10n_bg_price_diff_income_account_id = fields.Many2one(
        'account.account',
        string='Price Difference Income (−)',
        company_dependent=True,
        check_company=True,
        help='Income account used when the vendor invoice price is lower than the PO price. '
             'The difference is booked directly as financial income without chain traversal.',
    )

    # Сметка за брак/липса (напр. 669.200) — дебитира се при scrap или
    # отрицателна inventory adjustment. Без отделна сметка системата ползва
    # l10n_bg_stock_output_account_id (COGS), което осчетоводява брак като
    # реализирана продажба — счетоводно грешно.
    l10n_bg_stock_loss_account_id = fields.Many2one(
        'account.account',
        string='Stock Loss Account (брак/липси)',
        company_dependent=True,
        check_company=True,
        help='Expense account debited for scrap and negative inventory '
             'adjustments (e.g. 669.200). Falls back to Stock Output Account '
             'if not set.',
    )

    # Сметка за излишък от инвентаризация (напр. 709.000) — кредитира се при
    # положителна inventory adjustment.
    l10n_bg_stock_gain_account_id = fields.Many2one(
        'account.account',
        string='Stock Gain Account (излишъци)',
        company_dependent=True,
        check_company=True,
        help='Income account credited for positive inventory adjustments '
             '(e.g. 709.000). Falls back to Stock Input Account if not set.',
    )
