# Copyright 2024 Rosen Vladimirov
# License OPL-1

{
    "name": "L10n Bg Assets",
    "summary": "Bulgarian tax depreciation rules based on Bulgarian law",
    "description": """
   Add rules for tax depreciation base Bulgarian law.

   Key Features:
   * Tax depreciation board calculation
   * Bulgarian law compliant depreciation methods
   * Freeze periods support
   * Percentage-based depreciation
   * Tax model templates
""",
    "version": "19.0.1.0.0",
    "license": "OPL-1",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria-ee",
    "category": "Accounting/Localizations",
    "price": 150.00,
    "currency": "EUR",
    "images": [
        "static/description/banner.png"
    ],
    "depends": [
        "l10n_bg",
        "account_asset",
        "account_reports",
        # 'l10n_bg_config',
        # 'account_asset_product',
    ],
    "data": [
        "security/ir.model.access.csv",
        # "data/asset_report_base.xml",
        "data/asset_report.xml",
        "data/account_report_actions.xml",
        "data/menuitems.xml",
        "views/account_asset_views.xml",
    ],
    "demo": [],
    'countries': ['BG'],
    "installable": True,
    "application": False,
    "auto_install": False,
}
