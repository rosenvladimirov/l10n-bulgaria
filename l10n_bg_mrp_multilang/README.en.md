# Bulgaria — Multilingual MRP Workcenter

> Makes the MRP workcenter name translatable so manufacturing
> documents print bilingually like the rest of the localization.

**Module:** `l10n_bg_mrp_multilang` | **Version:** 18.0.1.0.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

The multilang stack (`partner_multilang` / `l10n_bg_multilang`) makes
partner/employee/bank names bilingual. Manufacturing documents
(work orders, BoM printouts) also show the **workcenter** name — this
one-field module makes it translatable too, so MRP paperwork stays
consistent with Bulgarian bilingual requirements.

## What it does

`mrp.workcenter` — `name` set `translate=True`. Nothing else.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `mrp` | (pairs with `l10n_bg_multilang`) |

## Configuration

None. Install — workcenter names accept per-language values.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Multilang core: `partner_multilang`, `l10n_bg_multilang`
- Sibling: `l10n_bg_project_multilang`
