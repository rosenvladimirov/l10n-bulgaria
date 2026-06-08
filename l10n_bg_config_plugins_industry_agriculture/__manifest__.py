# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Bulgaria - Industry Pack: Agriculture, Forestry & Fishing",
    "summary": """
        Industry configuration pack for КИД sector A (Agriculture, Forestry & Fishing):
        presets the company's active КИД sector so the chart-of-accounts
        install filter loads this sector's accounts, and is the home for
        the sector's accounting content (accounts / taxes / fiscal
        positions / analytic).""",
    "description": """
Bulgaria - Industry Pack: Agriculture, Forestry & Fishing (КИД sector A)
==================================================

Configuration pack for КИД sector A — agriculture, forestry and fishing (biological assets under СС 41, produce/WIP under СС 2).

What it does
------------
* On install, adds КИД section **A** to every Bulgarian company's
  *Active КИД sectors* (``res.company.l10n_bg_kid_ids``) and reloads
  the chart of accounts, so the "one chart, many КИД" install filter
  (``l10n_bg_config``) lets sector A's sector-specific accounts
  through.
* Is the designated home for sector A's accounting content shipped
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
    "version": "19.4.1.0.0",
    "development_status": "Alpha",
    "category": "Accounting/Localizations",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
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
