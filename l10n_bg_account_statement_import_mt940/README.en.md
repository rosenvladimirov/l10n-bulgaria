# Bulgaria — MT940 Bank-Statement Import

> Adds the SWIFT **MT940** statement format to Odoo's bank-statement
> import, with the `:28C:` StatementNumber pattern relaxed to accept
> Bulgarian-bank exports.

**Module:** `l10n_bg_account_statement_import_mt940` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

Most Bulgarian banks export account statements in **MT940** (SWIFT).
Odoo's core import doesn't list MT940; and the standard `mt940`
Python library's `StatementNumber` regex is stricter than what some
Bulgarian banks emit. This module registers the format and patches the
pattern so those exports parse cleanly.

## What it does

- `_get_bank_statements_available_import_formats()` extended to append
  `"mt940"` to the supported formats.
- `mt940.tags.StatementNumber.pattern` overridden with a relaxed
  regex so the `:28C:` field from Bulgarian banks is accepted.

## Dependencies

| Odoo core | Bulgarian-localization | External Python |
|---|---|---|
| `account_statement_import` base | `l10n_bg` | `mt940` |

## Configuration

1. Install (`pip install mt940` if not already present).
2. Accounting → import a bank statement → choose the **MT940** format
   → upload the bank's `.940` / `.sta` file.

## Note vs InfoPay

For Borica InfoPay banks, prefer the live API (`l10n_bg_infopay` +
bridges) over MT940 file import. MT940 is the fallback for banks
without an InfoPay channel.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Live alternative: `l10n_bg_infopay`
