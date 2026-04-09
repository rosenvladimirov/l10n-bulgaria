{
    'name': 'Bulgaria - Stock Auto Accounting',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Auto-post journal entries at picking validation for manual/periodic costing',
    'description': """
        Enables automatic stock accounting journal entries at picking validation
        for products using manual/periodic costing (product categories with
        'Auto-post stock accounting on validate' enabled).

        Standard Odoo v19 only creates accounting entries at picking time for
        'real_time' (perpetual) products. This module extends that mechanism to
        allow manual/periodic products to also generate entries, using the
        Bulgarian stock accounting standard:

            Dr. Stock Valuation Account (302/303/304)
            Cr. Stock Variation Account (GRNI / clearing)

        Works in combination with l10n_bg_stock_price_diff for price difference
        corrections between PO price and vendor invoice price.
    """,
    'author': 'BLC',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'license': 'LGPL-3',
    'depends': [
        'stock_account',
    ],
    'data': [
        'views/product_category_views.xml',
    ],
    'installable': True,
    'application': False,
}
