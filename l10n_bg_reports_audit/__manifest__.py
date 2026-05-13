{
    "name": "Bulgarian Accounting Reports Base",
    "version": "18.0.13.0.0",
    "development_status": "Production/Stable",
    "maintainers": ["rosenvladimirov", "deyanlyubenov"],
    "description": """
Bulgarian Accounting Reports — Base Module
==========================================

Technical foundation for Bulgarian accounting and tax reporting in Odoo 18.

Provides the SQL query layer, account tag configurations, and report
infrastructure required by all Bulgarian localization reporting modules.

Compliant with current NRA (НАП) requirements and Bulgarian accounting
standards (НСС / МСФО).

Coverage
--------
- Account tag definitions for Bulgarian chart of accounts
- SQL-based report queries optimized for large databases
- Base security model for report access control
- Foundation for VAT, audit, and tax administration reports

Extended Modules
----------------
This module is the base for the following advanced reporting solutions:

**l10n_bg_vat_reports**
  VAT Purchase/Sales ledgers and VIES declaration in NRA CSV format.
  Automated generation and submission workflow.

**l10n_bg_tax_admin**
  Tax administration protocols — Art. 117, Art. 82, Art. 163a.
  Self-assessment VAT document automation.

For information and demo: rosenvladimirov@gmail.com

Maintainers
-----------
Rosen Vladimirov — https://github.com/rosenvladimirov
OCA Bulgaria — https://github.com/OCA/l10n-bulgaria
""",
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
        "data/account_account_tag_god_balance.xml",
        "data/account_account_tag_god_pl.xml",
        "data/account_account_tag_god_equity.xml",
        "data/account_account_tag_god_cf.xml",
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
