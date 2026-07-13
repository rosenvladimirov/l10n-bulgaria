# Bulgaria — Cities & ЕКАТТЕ Geographic Database

> The authoritative Bulgarian settlement database: 28 regions, 265
> municipalities, ~3000 city halls, 5000+ settlements — all carrying
> their official ЕКАТТЕ codes.

**Module:** `l10n_bg_city` | **Version:** 18.0.1.1.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

Bulgarian official documents, NRA declarations, Intrastat filings and
NSI statistical reports all require the **ЕКАТТЕ** code (Единен
класификатор на административно-териториалните и териториалните
единици — the national settlement classifier). This module preloads
the full hierarchy so addresses are picked from a standardized list
rather than typed free-form, eliminating the typos that break legal
filings.

## Data model

### `res.city.types` (new)

Settlement-type taxonomy: град (city), село (village), градче,
квартал, манастир (monastery), жп гара (railway station), … Each row
carries a `code` and a translatable `name`.

### `res.city` (extended)

| Field | Meaning |
|---|---|
| `l10n_bg_ecattu` | The 5-digit ЕКАТТЕ code — the join key for all official reporting |
| `l10n_bg_type_settlement_id` | M2O → `res.city.types` |
| `l10n_bg_city_hall_id` / `l10n_bg_city_hall_code` | Parent кметство |
| `l10n_bg_municipality_id` | Parent община |
| `l10n_bg_has_tax_office` | Marks settlements hosting an NRA office (consumed by `l10n_bg_tax_offices`) |
| `l10n_bg_structure_type` | `normal` / `cityhall` / `municipality` — drives the three-level hierarchy + domain filtering |

The hierarchy is **Settlement → City Hall → Municipality → Region**,
with smart domains preventing circular references and scoping
selection lists by country + structure type.

### `res.country.state` (extended)

`name` made translatable — full support for the 28 Bulgarian области
in both Bulgarian and English.

## Data loading

`post_init_hook` bulk-imports four CSVs from the module:

- `res.country.state.csv` — 28 regions
- `res.city.municipality.csv` — 265 municipalities
- `res.city.cityhall.csv` — city halls
- `res.city.csv` — 5000+ settlements

Plus `res_city_types.xml` (taxonomy) and `res_country_data.xml`.

## ЕКАТТЕ quarterly sync (since 18.0.1.1.0 — Phase 4.1)

`data/ir_cron_data.xml` ships an **inactive** quarterly cron driving
the `l10n.bg.ekatte.sync` model. When enabled it:

1. downloads the НСИ ЕКАТТЕ deposit (or uses a manually uploaded
   ZIP/DBF attachment for air-gapped sites),
2. parses the DBF tables via `dbfread` (cp1251),
3. upserts `res.city` records keyed by `l10n_bg_ecattu`.

Flexible column aliases absorb НСИ format drift between releases. The
cron is shipped disabled — an operator flips it on after validating
the column mapping against the current НСИ release.

**External Python:** `dbfread`, `requests`.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `base_address_extended`, `contacts` | — (foundational; sits low in the dependency graph) |

## Configuration

1. Install — `post_init_hook` loads the full dataset (one-time, ~30 s).
2. (Optional) Settings → enable the "EKATTE: Quarterly Sync" cron once
   the НСИ deposit format is verified; or run a manual sync from the
   `l10n.bg.ekatte.sync` form with an uploaded ZIP/DBF.

## Downstream consumers

`l10n_bg_tax_offices` (office settlement marking), `l10n_bg_intrastat`
(location codes), `l10n_bg_reports_audit` (geographic reporting),
`l10n_bg_company_registry`, address-completion across the localization.

## Known limitations

- EKATTE sync cron disabled by default until column mapping is
  validated against a real НСИ deposit ZIP.
- Initial post-init import is sizeable; expect a one-time delay on
  first install.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Phase 4.1 sync detail: `claude.ai/memory/project_payroll_personnel_roadmap_2026_05_13.md`
- `readme/` — DESCRIPTION / CONTEXT source notes
