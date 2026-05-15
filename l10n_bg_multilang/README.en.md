# Bulgaria — Multilingual Core Records

> Extends the `partner_multilang` transliteration engine beyond
> partners to employees, banks, warehouses, currencies, resources and
> regions — so every record that prints on a Bulgarian document is
> bilingual.

**Module:** `l10n_bg_multilang` | **Version:** 18.0.0.1.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

`partner_multilang` makes `res.partner` names multilingual + auto
transliterated. But a Bulgarian invoice/payroll document also prints
employee names, bank names, warehouse names and currency labels —
those need the same bilingual treatment. This module applies the
`res.transliterate.mixin` and `translate=True` to that wider set of
core models.

## Extended models

| Model | Translatable field(s) | Mixin |
|---|---|---|
| `hr.employee` | `name` | + `res.transliterate.mixin` |
| `res.country.state` | `name` | + `res.transliterate.mixin` |
| `res.bank` | `name` | — |
| `stock.warehouse` | `name` | — |
| `res.currency` | `symbol`, `currency_unit_label`, `currency_subunit_label` | — |
| `resource.resource` | `name` | — |
| `res.country` | (translatable hooks) | — |

Employee and country-state get the full transliteration mixin (auto
Cyrillic→Latin + multilingual `display_name`); the rest get
`translate=True` so values can be maintained per language and printed
correctly on documents/reports.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| (hr/stock/resource base) | `partner_multilang` |

Hard dependency on `partner_multilang` — the transliteration engine
and JSONB-name infrastructure live there.

## Configuration

No configuration. Once installed, the listed models accept per-language
values; transliteration follows the `partner_multilang` company toggle
(**Transliterate Names**).

## Why a separate module

Kept distinct from `partner_multilang` so a deployment that only needs
multilingual *partners* (e.g. a pure-sales setup) isn't forced to
translate HR/stock/resource models it doesn't print.

## Known limitations

- Inherits all `partner_multilang` caveats (JSONB-name handling for
  raw SQL, short-string detection).
- `res.currency` label translation affects display only; accounting
  amounts are unaffected.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Engine: `partner_multilang`
- Sibling extensions: `l10n_bg_mrp_multilang`, `l10n_bg_project_multilang`
