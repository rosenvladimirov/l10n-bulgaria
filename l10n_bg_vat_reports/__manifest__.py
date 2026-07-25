{
    "name": "Bulgarian Accounting Reports",
    "version": "16.0.1.2.0",
    "category": "Accounting/Localizations/Reporting",
    "summary": "Reporting for Bulgarian Localization",
    "license": "OEEL-1",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria-ee",
    "depends": [
        "base",
        "sale",
        "account",
        "l10n_bg",
        "l10n_bg_config",
        "account_reports",
    ],
    "data": [
        "data/account_tax_report_declaration_data.xml",
        "security/ir.model.access.csv",
        "views/account_bg_vat_line_sale_reports.xml",
        "views/account_bg_vat_line_purchase_reports.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_vat_reports/static/src/scss/vat_reports.scss",
        ],
    },
    "auto_install": [
        "l10n_bg",
        "account_reports"
    ],
    "post_load": "post_load_hook",
    "installable": True,
}
