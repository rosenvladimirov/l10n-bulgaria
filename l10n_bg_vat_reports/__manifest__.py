{
    "name": "Bulgarian Accounting Reports (EE)",
    "version": "19.0.3.0.5",
    "application": False,
    "development_status": "Production/Stable",
    "maintainers": ["rosenvladimirov"],
    "category": "Accounting/Localizations/Reporting",
    "summary": "Reporting for Bulgarian Localization. EE version.",
    "description": """
    Specialized module for generating accounting reports and declarations in compliance with Bulgarian legislation.

    Functional capabilities:
    VAT Return (VAT Declaration under Art. 125 of the Bulgarian VAT Act) • Sales and Purchase Ledgers (under Art. 124 of the Bulgarian VAT Act) • EC Sales List (VIES Declaration under Art. 125 of the Bulgarian VAT Act).

    Integration with National Revenue Agency (NRA) systems:
    Automated generation of CSV files conforming to approved formats • Built-in validation according to NRA technical requirements • Report export in PDF and Excel formats • Chronological tracking of submitted declarations

    Compliant with the latest changes in tax and accounting legislation.
    """,
    "author": "Rosen Vladimirov, Deyan Lyubenov",
    "license": "OPL-1",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria-ee",
    "depends": [
        "base",
        "sale",
        "account",
        "l10n_bg",
        "l10n_bg_config",
        "l10n_bg_reports_audit",
        "account_followup",
        "account_reports",
    ],
    "data": [
        "data/account_tax_report_declaration_data.xml",
        "views/reports.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_vat_reports/static/src/components/**/*",
        ],
        "web.report_assets_common": [
            "l10n_bg_vat_reports/static/reports/layout_assets/layout_print.scss",
        ]
    },
    "auto_install": [
        "l10n_bg",
        "account_reports"
    ],
    'images': [
        'static/description/banner.png',
    ],
    "installable": True,
    "price": 250,
    "price_currency": "EUR",
}
