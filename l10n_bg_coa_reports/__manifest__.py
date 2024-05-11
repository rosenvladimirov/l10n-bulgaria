{
    "name": "Bulgarian Accounting Reports",
    "version": "16.0.1.0.0",
    "category": "Accounting/Localizations/Reporting",
    "summary": "Reporting for Bulgarian Localization",
    "depends": [
        "l10n_bg",
        "account_reports",
    ],
    "data": [
        "report/account_bg_vat_line_view.xml",
        "data/account_financial_report_data.xml",
        "report/account_bg_vat_line_purchase_view.xml",
        # 'views/res_config_settings_view.xml',
        "security/ir.model.access.csv",
    ],
    "auto_install": ["l10n_bg", "account_reports"],
    "installable": True,
    # 'license': 'OEEL-1',
}
