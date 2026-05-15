# Account Statement Import Mt940

**Module:** `l10n_bg_account_statement_import_mt940` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** ?

## Overview

Part of the **l10n-bulgaria** repository — see the repo-level README for context.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `account_statement_import_file` | — |

**External Python packages:** `mt-940`

## Extended models

- `account.journal` (inherited)

## Wizards

- `wizard/account_statement_import.py`
- `wizard/bank_custom_tags.py`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_account_statement_import_mt940' or via CLI:
odoo -i l10n_bg_account_statement_import_mt940 -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)
- Module tests: `tests/`

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
