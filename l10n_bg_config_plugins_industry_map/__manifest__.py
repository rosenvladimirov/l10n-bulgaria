# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Bulgaria - Account ↔ КИД Industry Mapping Plugin",
    "summary": """
        Seed data plugin for the КИД ↔ chart-of-accounts mapping used to
        derive a company's primary economic activity (НСИ methodology).""",
    "description": """
Bulgarian Account ↔ КИД Industry Mapping (seed plugin)
======================================================

Ships the localization default ``l10n.bg.account.industry.map`` dataset
(loaded through the standard ``account.chart.template`` plugin pipeline
of ``l10n_bg_config``). The mapping is *typed*
(mandatory / characteristic / forbidden) and flags the net-sales-revenue
accounts (701 / 702 / 703 / 704) used by the reverse derivation of the
company's primary КИД section, following the НСИ methodology (main
activity = highest relative share of net sales revenue).

Sources / rationale (carried in the ``note`` of every row): СС 2
(inventories), СС 11 (construction contracts), СС 18 (revenue), СС 41
(agriculture), СС 9 (non-profit). Finance/insurance (sector K) and
budget entities (sector O) are intentionally out of scope — they use
separate accounting frameworks (БНБ/КФН МСФО, budget chart) and are not
covered by the national chart of accounts.
    """,
    "version": "19.0.1.0.4",
    "development_status": "Beta",
    "category": "Accounting/Localizations",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "account",
        "l10n_bg_config",
    ],
    "data": [
        "data/l10n.bg.account.industry.map.csv",
        "data/l10n_bg_account_kid_rule.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
    "maintainers": ["rosenvladimirov"],
    "tags": ["localization", "accounting", "bulgaria", "nsi", "kid"],
    "odoo_version": "19.0",
    "python_version": ">=3.11",
    "countries": ["BG"],
}
