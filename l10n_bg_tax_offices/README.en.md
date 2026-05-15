# Bulgaria — Tax / Social-Security Office Directory

> Preloaded `res.partner` directory of every NRA territorial office,
> NSSI regional directorate and NSI statistical bureau — so documents
> and partners can reference the correct authority.

**Module:** `l10n_bg_tax_offices` | **Version:** 18.0.1.1.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

Bulgarian businesses correspond with three authorities by region: the
**NRA** (НАП — taxes), **NSSI** (НОИ — social security) and **NSI**
(НСИ — statistics). This module ships the full, current directory as
`res.partner` records (parent → office hierarchy) so a company can be
linked to the right office for reporting and document automation.

## Data (~80 res.partner records, refreshed 2026-05-15 — Phase 4.4)

### `data/res_tax_offices.xml` — NRA / НАП

- NRA central + executive director (Milena Krastanova, since 2026-03-09)
- 5 Territorial Directorates (ТД): Sofia, Plovdiv, Varna, Burgas, Veliko Tarnovo
- Дирекция ГДО (large taxpayers, ul. Aksakov 29) + 4 СДО (medium taxpayers)
- 22 oblast offices, each parented to its ТД, with the official
  `td_<oblast>@ro<NN>.nra.bg` email pattern (ro01=Благоевград …
  ro29=ГДО)

### `data/res_noi_offices.xml` — NSSI / НОИ

- NSSI central + manager (Vesela Karaivanova-Nacheva, since 2025-07-24)
  + deputy
- **28 Regional Directorates (ТП)** with current address, phone,
  `<City>@nssi.bg` email and director name (sourced live from
  nssi.bg, 2026-05-15)

### `data/res_nsi_offices.xml` — NSI / НСИ

- NSI central + **6 Territorial Statistical Bureaus** (Northwest /
  North / Northeast / Southeast / South / Southwest), each carrying
  its oblast coverage in the `comment` field

## Email/code conventions (for future refreshes)

- NRA: `td_<oblast>@ro<NN>.nra.bg`; NN per oblast (ro22=София-град,
  ro23=София-област, ro29=ГДО)
- NOI: `<Cityname>@nssi.bg` — legacy spellings: `Vratza@`,
  `Velikotarnovo@` (no hyphen), `Sofiaregion@` (София-област)
- See `claude.ai/memory/reference_nra_obr55_okd5_formats.md` +
  `project_session_2026_05_14_overnight_ready_for_tests.md` for the
  full code map and verification notes (NRA TD-level director names
  were not capturable — nra.bg requires JS/reCAPTCHA).

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| (contacts base) | `l10n_bg`, `l10n_bg_city` |

`l10n_bg_city` provides the settlement records the offices reference
(`l10n_bg_has_tax_office`).

## Configuration

Install — the directory loads as partners (hierarchical: authority →
TD/RD → oblast office). Link a company's tax office on its partner for
report/automation use.

## Maintenance

Contact data drifts (directors change, offices relocate). Refresh
quarterly: re-run the Phase 4.4 web-research flow, regenerate the 3
data XMLs, bump 1.1.x. NOI data is fully authoritative (scraped
nssi.bg); NRA phones came from a 2011 mirror cross-checked against
recent sources — re-verify against nra.bg before relying on a specific
office phone.

## Known limitations

- NRA TD-level director names absent (source gated behind reCAPTCHA).
- `noupdate=0` data — a module upgrade re-applies the XML; manual edits
  to these partners are overwritten on `-u`.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Refresh provenance: `claude.ai/memory/project_session_2026_05_14_overnight_ready_for_tests.md`
- Settlement source: `l10n_bg_city`
