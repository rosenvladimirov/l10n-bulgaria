# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Bulgaria - Waste Management (Permits & Quotas)",
    "version": "19.4.1.0.0",
    "summary": "Bulgarian waste treatment permits with annual quotas and "
               "real-time usage tracking against actual stock movements",
    "description": """
Bulgaria Localization - Waste Permits and Quotas
================================================

Models the regulatory permits issued by RIOSV / IAOS / МОСВ that grant the
right to treat waste (Art. 35 / 67 / 78 of ЗУО) and tracks the operating
quotas per code × site × activity in real time.

**Models**
----------

* `l10n.bg.waste.permit` — permit header (number, dates, issuing authority,
  draft / active / suspended / expired / revoked state with mail tracking).
* `l10n.bg.waste.permit.line` — quota row (waste_code × site × activity)
  with `annual_quota_kg`, `max_storage_kg` and computed `quota_used_ytd_kg`,
  `quota_remaining_kg`, `quota_percent_used`, `current_storage_kg`.

**Usage compute**
-----------------

The `_compute_usage` method aggregates `stock.move.line` records whose
`waste_code_id` matches the permit line, filtered to the destination
warehouse(s) linked to the site, and only for the current calendar year.
The aggregate is recomputed on demand (not stored — kept as
``compute=False, store=False`` for free invalidation).

When the companion module `l10n_bg_waste_picking` is not installed (the
`waste_code_id` column on `stock.move.line` does not yet exist), the
compute degrades gracefully and returns zeros.

**Companion modules**
---------------------

* `l10n_bg_waste_base`    — catalog of codes, activities, sites (required)
* `l10n_bg_waste_picking` — populates the real movements that this module
  aggregates (required for non-zero usage values)
* `l10n_bg_waste_report`  — XLSX exports per Annex 4 / 18
""",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "category": "Localization/Bulgaria",
    "license": "AGPL-3",
    "depends": [
        "l10n_bg_waste_base",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "views/waste_permit_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
