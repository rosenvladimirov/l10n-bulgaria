{
    "name": "Bulgarian Accounting Reports",
    "version": "18.0.7.0.4",
    "development_status": "Production/Stable",
    "maintainers": ["rosenvladimirov", "deyanlyubenov"],
    "description": "Reporting for Bulgarian Localization technical module.",
    "category": "Accounting/Localizations/Reporting",
    "summary": """
    Reporting for Bulgarian Localization technical module
    """,
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "base",
        "sale",
        "account",
        "l10n_bg",
        "l10n_bg_config",
    ],
    "data": [
        "data/account_account_tag_function.xml",
        "security/ir.model.access.csv",
        "wizards/account_account_tag_bulk_edit_wizard.xml",
        "views/account_bg_vat_line_sale_reports.xml",
        "views/account_bg_vat_line_purchase_reports.xml",
        "views/account_bg_vat_line_vies_reports.xml",
        "views/account_bg_partner.xml",
        "views/account_bg_products.xml",
        "views/account_account_tag_views.xml",
        "views/product_view.xml",
        "views/res_partner.xml",
        "views/account_move_views.xml",
        "views/res_config_view.xml",
        "views/res_company_views.xml",
        "views/account_menuitem.xml",
    ],
    "installable": True,

    'images': [
        'static/description/banner.png',
    ],

    'tags': ['localization', 'accounting', 'bulgaria', 'configuration'],

    # Version requirements
    'odoo_version': '18.0',
    'python_version': '>=3.11',
}
