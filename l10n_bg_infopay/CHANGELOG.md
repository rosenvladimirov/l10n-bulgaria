# Changelog

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
