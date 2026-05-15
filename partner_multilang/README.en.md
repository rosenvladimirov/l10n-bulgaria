# Partner Multilang — Transliteration & Multilingual Names

> Automatic Cyrillic→Latin transliteration (ISO 9 / ΕΛΟΤ 743), language
> detection, multi-language partner search and correct sorting — the
> infrastructure that makes Bulgarian partner data legally compliant
> and usable in mixed-script databases.

**Module:** `partner_multilang` | **Version:** 18.0.3.0.3 | **License:** AGPL-3 | **Category:** Localization

## Overview

Cyrillic-script countries (Bulgaria, Russia, Serbia, Macedonia,
Ukraine, Belarus) legally require a Latin transliteration of names on
official documents. Mixed Cyrillic/Latin data also sorts incorrectly
in Odoo list/kanban views (Cyrillic "Г" vs Latin "G" land in different
positions). This module solves both: it transliterates automatically,
stores every translation, searches across all of them, and sorts by
the user's language.

## Architecture

### `res.transliterate.mixin` (new AbstractModel)

The reusable engine. Any model that inherits it gets multilingual
`display_name`:

- `_compute_display_name()` override — Odoo 18 uses a computed
  `display_name` instead of `name_get()`; this returns the value in
  the user's language, transliterating on the fly when needed.
- `transliterate_tracking` (Json) — records which fields were
  auto-transliterated, so manual edits aren't overwritten.

### Language detection (two-tier)

- **Priority 1:** `lingua` (`LanguageDetectorBuilder`) — accurate.
- **Priority 2:** `langdetect` — fast fallback.

`detect_text_language(text)` picks the script; `partner_name_translate
(name, lang, flag)` transliterates non-English names (ISO 9 for
Cyrillic, ΕΛΟΤ 743 for Greek) via the `transliterate` + `unidecode`
libraries.

### `res.partner` (extended)

- `name`, `street`, `street2`, `city`, `function`, `company_name`,
  `commercial_company_name` made `translate=True`; `name` gets a
  trigram index for fast multilingual search.
- `complete_name_multilanguage` — a **JSONB column** added via raw
  SQL `ADD COLUMN IF NOT EXISTS` so the technical field materializes
  **without a module upgrade**.
- `_rec_names_search()` override — search matches any stored
  translation, not just the active language.

### Other extensions

| Model | Why |
|---|---|
| `ir.binary` | `download_name` handling for translated JSONB names (avoids broken filenames with newlines/Cyrillic) |
| `res.country.state` | `name` translatable |
| `res.lang` | sort/collation hooks |
| `res.config.settings` | `transliterate_names` company toggle |

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `base`, `contacts` | — (foundational; no l10n deps) |

**External Python:** `transliterate`, `unidecode`, `lingua`.

## Configuration

1. Install.
2. Settings → enable **Transliterate Names** (per company).
3. Existing partners transliterate on next write; new partners on
   create. The JSONB column appears automatically — no `-u` needed.

## JSONB caveat for downstream modules

Because translated names live in PostgreSQL **JSONB** columns, any
module doing `regexp_matches` / raw SQL on partner names must handle
the JSONB shape. This is a recurring gotcha — see
`l10n_bg_account_reconcile_patch` and `hr_org_chart_multilang_fix`,
which exist precisely to fix JSONB-name handling in core/3rd-party
code.

## Downstream consumers

`l10n_bg_multilang`, `l10n_bg_mrp_multilang`,
`l10n_bg_project_multilang`, and effectively every report that prints
partner names bilingually.

## Known limitations

- Transliteration is rule-based (ISO 9 / ΕΛΟΤ 743); proper names with
  non-standard romanization need manual override (tracked via
  `transliterate_tracking`).
- Language detection on very short strings (1-2 chars) is unreliable —
  falls back to the active language.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- JSONB-fix consumers: `l10n_bg_account_reconcile_patch`, `hr_org_chart_multilang_fix`
- `readme/` — DESCRIPTION / CONTEXT source notes
