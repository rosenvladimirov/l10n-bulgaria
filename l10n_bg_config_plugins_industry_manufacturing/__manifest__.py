# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Bulgaria - Industry Pack: Manufacturing",
    "summary": """
        Industry configuration pack for КИД sector C (Manufacturing):
        presets the company's active КИД sector so the chart-of-accounts
        install filter loads this sector's accounts, and is the home for
        the sector's accounting content (accounts / taxes / fiscal
        positions / analytic).""",
    "description": """
Bulgaria - Industry Pack: Manufacturing (КИД sector C)
==================================================

Configuration pack for КИД sector C — manufacturing (produce/WIP under СС 2, excise duties under ЗАДС).

What it does
------------
* On install, adds КИД section **C** to every Bulgarian company's
  *Active КИД sectors* (``res.company.l10n_bg_kid_ids``) and reloads
  the chart of accounts, so the "one chart, many КИД" install filter
  (``l10n_bg_config``) lets sector C's sector-specific accounts
  through.
* Is the designated home for sector C's accounting content shipped
  through the standard ``account.chart.template`` plugin pipeline
  (``data/template/account.account-bg.csv``, ``account.tax-bg.csv``,
  ``account.fiscal.position-bg.csv``).

ACCOUNTING REVIEW PENDING
-------------------------
The sector accounting content (``data/template/*.csv``) is intentionally
left empty — it must be filled from sourced Bulgarian accounting
standards, not improvised. See README for the open decomposition design
point regarding shared КИД account-code rules.
    """,
    "version": "19.0.1.0.0",
    "development_status": "Alpha",
    "category": "Accounting/Localizations",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "account",
        "l10n_bg_config",
    ],
    "data": [],
    "demo": [],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
    "application": False,
    "maintainers": ["rosenvladimirov"],
    "tags": ["localization", "accounting", "bulgaria", "kid", "industry"],
    "odoo_version": "19.0",
    "python_version": ">=3.11",
    "countries": ["BG"],
}
