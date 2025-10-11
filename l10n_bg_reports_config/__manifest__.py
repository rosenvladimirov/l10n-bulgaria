{
    "name": "Bulgarian Accounting Reports Configuration",
    "version": "18.0.7.0.6",
    "development_status": "Production/Stable",
    "maintainers": ["rosenvladimirov", "deyanlyubenov"],
    "description": "Configuration and views for Bulgarian Accounting Reports (Odoo 18.0).",
    "category": "Accounting/Localizations/Reporting",
    "summary": """
    Configuration module for Bulgarian Accounting Reports - Odoo 18.0 specific views and wizards
    """,
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "l10n_bg_reports_audit",
        "l10n_bg_config",
    ],
    "data": [
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
    "auto_install": False,
    "application": False,
    "images": [
        "static/description/banner.png",
    ],
    "tags": ["localization", "accounting", "bulgaria", "reporting", "configuration"],
    "countries": ["BG"],
    # Version requirements
    "odoo_version": "18.0",
    "python_version": ">=3.11",
}
