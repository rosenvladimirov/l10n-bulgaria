{
    "name": "Bulgarian Accounting Reports Base",
    "version": "11.0.1",
    "development_status": "Production/Stable",
    "maintainers": ["rosenvladimirov", "deyanlyubenov"],
    "description": "Technical base module for Bulgarian accounting reports with SQL queries and tag configurations.",
    "category": "Accounting/Localizations/Reporting",
    "summary": """
    Technical base module for Bulgarian accounting reports - SQL queries and tag configurations
    """,
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "base",
        "account",
        "l10n_bg",
        "l10n_bg_ledger",
        "l10n_bg_config",
    ],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "images": [
        "static/description/banner.png",
    ],
    "tags": ["localization", "accounting", "bulgaria", "technical"],
    "countries": ["BG"],
    # Version requirements
    "python_version": ">=3.11",
}
