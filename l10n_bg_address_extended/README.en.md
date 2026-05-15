# Bulgaria — Extended Address Components

> Granular Bulgarian address fields — street / number / block / floor /
> entrance / sector — beyond Odoo's two-line `street`/`street2`, kept
> in sync between company and its partner.

**Module:** `l10n_bg_address_extended` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

A legally correct Bulgarian address is structured: улица + № + блок +
вход + етаж + район. Odoo's base address is just two free-text lines,
which loses that structure for official documents and NRA reporting.
This module adds the discrete components on top of
`base_address_extended` and keeps the company record and its partner
record consistent.

## Extended models

### `res.company` / `res.partner`

| Field | Bulgarian meaning |
|---|---|
| `street_name` | улица (name only) |
| `street_number` | № |
| `street_number2` | secondary number |
| `street_building_number` | блок |
| `street_floor_number` | етаж |
| `street_sector_number` | район / sector |
| `city_id` | M2O → `res.city` (the ЕКАТТЕ settlement) |

Each component has an `inverse` method so editing it on the company
writes through to `company.partner_id` (and vice-versa) — the two
never drift. `_get_company_address_field_names()` is extended so these
fields participate in standard company-address handling.
`country_enforce_cities` is exposed (related from the partner's
country) to drive city-selection enforcement.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `base_address_extended` | (sits low; pairs with `l10n_bg_city`) |

## Configuration

No configuration. Once installed, the extra address fields appear on
company and partner forms; `city_id` links to the `l10n_bg_city`
ЕКАТТЕ database for standardized settlement selection.

## Why it matters

NRA declarations, invoices and the Trade Registry integration all
expect the address broken into components. Storing блок/вход/етаж as
discrete fields (not crammed into `street2`) is what makes
machine-generated official documents correct.

## Known limitations

- Pure structural module — does not validate that the number/block
  combination actually exists for the chosen settlement.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Settlement source: `l10n_bg_city`
- Consumers: `l10n_bg_company_registry`, `l10n_bg_api_nra`, report theme
