# Bulgaria — Account Reconcile JSONB-Name Fix

> Patches bank-statement reconciliation so partner matching works when
> partner names are stored as translatable JSONB (the
> `partner_multilang` side-effect).

**Module:** `l10n_bg_account_reconcile_patch` | **Version:** 18.0.1.0.0 | **License:** OPL-1 | **Category:** Localization

## Overview

When `partner_multilang` makes `res.partner.name` a translatable
**JSONB** column, Odoo's bank-statement reconciliation partner-matching
runs `regexp_matches` against the raw JSONB and fails to find the
partner. This module monkey-patches the matching logic to resolve the
JSONB name first, so auto-reconciliation keeps working in a
multilingual database.

## What it does

Via a `post_load_hook` (monkey-patch, no model changes):

- `_retrieve_partner_patch` — replaces the partner-retrieval logic;
  the SQL `regexp_matches(...)` now operates on the resolved name text
  instead of the JSONB blob.
- `_get_st_line_strings_for_matching` — adjusted so the statement-line
  strings compare against the proper name representation.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `account_accountant` (reconcile) | effective with `partner_multilang` |

## Configuration

None. Install — reconciliation partner matching tolerates JSONB names.

## Related JSONB-fix modules

Companion to `hr_org_chart_multilang_fix` (org-chart JSONB names).
Root cause documented in `partner_multilang`.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Root cause: `partner_multilang`
