# Changelog

## 18.0.1.1.0 (2026-03-24)

### Fixed
- Replaced OCA dependency `account_statement_import_base` with Odoo core `account` module
- Removed OCA-specific methods (`_statement_line_import_speeddict`, `_statement_line_import_update_hook`, `_statement_line_import_update_unique_import_id`) from `account_journal.py`
- Fixed `_check_credentials` in `res_users.py` — converted from `@classmethod` to instance method for Odoo 18.0 API compatibility
- Fixed `_infopay_distribute_token` — converted from `@classmethod` to instance method

## 18.0.1.0.0 (2025-03-22)

### Added
- InfoPay REST API client (`infopay.provider`) — session, accounts, transactions, payments
- Bank statement sync from InfoPay transactions (`account.journal._infopay_sync_statements`)
- Account discovery by IBAN (`_infopay_discover_accounts`)
- Single payment submission — BGN domestic, EUR SEPA, BGN budget/tax
- Bulk payment submission (2–250 payments per batch)
- Payment status polling (`_infopay_check_status`, `_infopay_pull_status`, `_infopay_pull_all_pending`)
- InfoPay access token stored encrypted in `l10n_bg_bank_wallet` crypto wallet
- Token distribution at login — copies token to authenticated user's wallet (`res_users._infopay_distribute_token`)
- Dual-strategy token retrieval — current user's wallet first, owner's wallet fallback for cron
