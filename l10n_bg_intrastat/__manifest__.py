# Copyright 2024 Rosen Vladimirov
# License OPL-1

{
    "name": "L10n BG Intrastat",
    "summary": "Bulgaria Intrastat XML Declaration Report",
    "description": """
   Bulgaria - Intrastat XML Report
   ===============================

   This module generates Intrastat XML report for declaration
   compliant with Bulgarian National Revenue Agency requirements.

   Features:
   ---------
   * XML export for Bulgarian Intrastat declarations
   * Support for both Arrivals and Dispatches
   * Automatic validation of required fields
   * Compatible with Odoo 19.0

   Requirements:
   -------------
   * account_intrastat
   * l10n_bg
   * l10n_bg_config
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations/Reporting",
    "license": "OPL-1",
    "author": "Rosen Vladimirov",
    "maintainer": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria-ee",
    "depends": [
        "account_intrastat",
        "l10n_bg",
        "l10n_bg_config",
        "l10n_bg_reports_audit",
    ],
    "data": [
        "views/res_config_settings.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
    "price": 150.00,
    "currency": "EUR",
    "images": [
        "static/description/banner.png",
    ],
    "support": "rosen.vladimirov@gmail.com",
}
