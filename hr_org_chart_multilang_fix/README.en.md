# HR Org Chart — Multilang JSONB Fix

> Resolves translatable JSONB employee names to plain strings before
> the `hr_org_chart` widget renders them — without this the org chart
> shows raw `{"en_US": ...}` dicts.

**Module:** `hr_org_chart_multilang_fix` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

When `partner_multilang` / `l10n_bg_multilang` make
`hr.employee.name` translatable, Odoo 18 stores it as a PostgreSQL
**JSONB** column. The `hr_org_chart` OWL widget receives the raw JSONB
dict and renders it literally (`{"en_US": "...", "bg_BG": "..."}`)
instead of the name. This patch resolves the value to a plain string
for the active language before it reaches the JavaScript layer.

## What it does

Overrides `_prepare_employee_data` and resolves every name-like field
from its JSONB form to the active-language string. If the multilang
modules are not installed (no JSONB), the patch is a **no-op** — safe
to install regardless.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `hr_org_chart` | (effective only with `l10n_bg_multilang`/`partner_multilang`) |

## Configuration

None. Install — the org chart renders proper names.

## Related JSONB-fix modules

This is one of the JSONB-name compatibility shims; the other is
`l10n_bg_account_reconcile_patch` (fixes JSONB names in bank-statement
reconciliation). See `partner_multilang` for the root cause.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Root cause: `partner_multilang` (JSONB names)
