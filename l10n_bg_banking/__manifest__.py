{
    'name': 'L10n BG Banking',
    "version": "18.0.0.0.0",
    'category': 'Localization',
    'summary': 'Banking integration for Bulgarian localization',
    'author': 'Rosen Vladimirov, Deyan Lyubenov',
    'license': 'OEEL-1',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria-ee',
    'depends': ["base", "account", "account_bank_statement_import"],
    'data': [
        'security/ir.model.access.csv',
        'views/res_bank_views.xml',
        'views/menu_items.xml',
    ],
}
