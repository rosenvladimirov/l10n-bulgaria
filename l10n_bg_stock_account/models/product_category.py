from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

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
