# Bulgaria — TARIC / HS / CN Code Management

> Customs commodity-code management for products and invoice lines,
> with a local cache of EU TARIC tariff rates pulled from the European
> CIRCABC dataset.

**Module:** `l10n_bg_tariff_code` | **Version:** 18.0.3.0.11 | **License:** LGPL-3 | **Category:** Localization

## Overview

Bulgarian customs declarations and Intrastat reporting require each
product to carry its **TARIC / HS / CN** commodity code, and customs
valuation needs the applicable tariff rate. Querying the EU TARIC
system on every line would be slow and rate-limited, so this module
maintains a **local rate cache** keyed by CN code + country + validity
window, refreshed from the official CIRCABC data.

## Data model

### `l10n_bg.taric.cache` (new)

Local cache of TARIC tariff rates from CIRCABC.

| Field | Meaning |
|---|---|
| `cn_code` | Combined Nomenclature code (rec name) |
| `country_code` | Origin country the rate applies to |
| `measure_type` | TARIC measure type (duty, anti-dumping, …) |
| `valid_from` / `valid_to` | Rate validity window |

Lookups hit the cache first; a miss (or stale entry past
`valid_to`) triggers a refresh from the configured TARIC API.

### Extended models

| Model | Addition |
|---|---|
| `product.template` / `product.product` | TARIC/HS/CN code fields |
| `account.move.line` | tariff code propagation for customs valuation |
| `res.company` | `l10n_bg_taric_api_url`, `l10n_bg_taric_api_enabled`, `l10n_bg_taric_cache_duration` (hours), default fallback rate, auto-download toggle |
| `res.config.settings` | exposes the above as settings |

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `product` (+ account base) | `l10n_bg` |

**External Python:** `requests`.

## Configuration

1. Settings → Bulgarian Localization → TARIC:
   - **Enable TARIC API** + **TARIC API URL** (EU endpoint).
   - **Cache Duration (hours)** — how long a cached rate is trusted.
   - Default fallback rate when a code can't be resolved.
2. Assign TARIC/CN codes on products (manually or via
   `taric_ai_classifier` for AI-assisted classification).

## Downstream consumers

`taric_ai_classifier` (AI classification writes codes here),
`l10n_bg_intrastat` (commodity codes on declarations),
`l10n_bg_tax_admin` customs flows.

## Known limitations

- Cache freshness depends on `cache_duration`; a rate that changes
  mid-window is only picked up after expiry (or manual refresh).
- CIRCABC dataset structure changes occasionally — the fetch layer
  tolerates common shifts but a major EU format change needs a code
  update.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- AI classifier: `taric_ai_classifier`
- Customs consumer: `l10n_bg_intrastat`, `l10n_bg_tax_admin`
