# Changelog

## 19.0.5.0.0 (2026-05-10) — BREAKING

### Changed
- **Security: `uniqueId` moved from plain field to wallet / Fernet.**
  The InfoPay uniqueId is paired with the accessToken — neither alone
  authenticates with the API, so they must sit on the same security
  boundary.  Previous releases stored uniqueId as a plain `Char` on
  `res.company`, while the access token was already encrypted.  This
  release closes that asymmetry.

  * **User-side**: `l10n_bg_infopay_unique_id` field is removed from
    `res.company`; uniqueId now lives in the user crypto wallet under
    key `infopay_unique_id` (alongside `infopay_access_token`).
  * **Admin-side**: `l10n_bg_infopay_admin_unique_id` field replaced
    with `l10n_bg_infopay_admin_unique_id_encrypted` — Fernet-encrypted
    with the same key as the admin token.

### Migration
- Pre-migration `19.0.5.0.0/pre-migration.py` drops the two old
  columns and warns when non-empty values are discarded.
- **Operators must re-set credentials after upgrade** — call
  `company._infopay_set_credentials(uid, tok)` for user-side and
  `company._l10n_bg_infopay_set_admin_credentials(uid, tok)` for
  admin (cron).
- `res.users._infopay_distribute_token` now copies BOTH wallet keys
  (uniqueId + token) at login, so the distribution still works for
  users who weren't the original setup user.

### Internal
- New helpers `_infopay_get_unique_id`, `_infopay_has_credentials`,
  `_l10n_bg_infopay_get_admin_unique_id`,
  `_l10n_bg_infopay_has_admin_credentials`.
- `infopay.provider._create_session` now reads from these helpers
  instead of touching company columns directly.

## 19.0.4.1.0 (2026-05-10)

### Added
- New `account.payment.method` records (`data/account_payment_method.xml`):
  - `l10n_bg_infopay_domestic_bgn` — BGN domestic + bulk
  - `l10n_bg_infopay_sepa_eur`   — SEPA EUR + bulk
  - `l10n_bg_infopay_budget_bgn` — BGN budget / tax (НАП)
  Codes consumed by the new payment bridge modules
  (`l10n_bg_infopay_oca_payment` for OCA, `l10n_bg_infopay_ee_payment`
  for EE) so neither bridge has to ship its own duplicate XML.

## 19.0.4.0.0 (2026-05-10) — BREAKING

### Changed
- All field names on **core public models** (`res.company`,
  `account.journal`, `account.payment`) introduced by this module are
  now prefixed `l10n_bg_*`, per the localization-wide rule that no
  upstream Odoo model receives unprefixed fields from БГ packages.
  - `res_company.infopay_unique_id` → `l10n_bg_infopay_unique_id`
  - `res_company.infopay_token_user_id` → `l10n_bg_infopay_token_user_id`
  - `account_journal.infopay_account_id` → `l10n_bg_infopay_account_id`
  - `account_journal.infopay_last_sync` → `l10n_bg_infopay_last_sync`
  - `account_payment.infopay_payment_id` → `l10n_bg_infopay_payment_id`
  - `account_payment.infopay_sca_url` → `l10n_bg_infopay_sca_url`
  - `account_payment.infopay_status` → `l10n_bg_infopay_status`
  - `account_payment.infopay_bulk` → `l10n_bg_infopay_bulk`
- Pre-migration script `migrations/18.0.4.0.0/pre-migration.py` does
  idempotent `ALTER TABLE RENAME COLUMN` for all 8 fields — existing
  data is preserved; views referring to the old names are recreated
  by the registry rebuild that follows the rename.

## 19.0.3.0.2 (2026-05-10)

### Fixed
- InfoPay invoice numbering now reads `account.move.l10n_bg_document_number`
  (provided by `l10n_bg_config`) instead of the raw move ID — yields
  the same number that lands on the printed VAT invoice (Art. 78 БГ
  ЗДДС).  Falls back to `move.id.zfill(10)` when the document number
  is empty or fails the InfoPay regex.

## 19.0.3.0.1 (2026-05-10)

### Fixed
- **Critical: race condition** in admin Fernet key bootstrap — wrapped
  `ICP.set_param` with `pg_advisory_xact_lock` + double-check; two
  concurrent transactions can no longer regenerate the key and lose
  records that were encrypted under the now-discarded value.
- **Critical: null pointer** in `_l10n_bg_infopay_payment_details_dict`
  when `partner_bank_id` is empty — defensive null check raises a
  clear UserError instead of `AttributeError`.
- **Critical: silent failure** in token-distribution login hook —
  changed log level from `DEBUG` to `WARNING` so missing wallet
  passwords surface in standard log routing.

## 19.0.3.0.0 (2026-05-10)

### Added
- `l10n.bg.infopay.statement.mixin` — abstract mixin for statement
  bridge modules.  Required overrides: `_l10n_bg_infopay_get_company`,
  `_l10n_bg_infopay_get_account_id`, `_l10n_bg_infopay_use_admin_token`.
  Concrete helpers: pull transactions, pull accounts, normalize +
  dedup statement lines, summarize balances.
- `l10n.bg.infopay.payment.mixin` — abstract mixin for payment bridge
  modules.  Wraps single + bulk + budget endpoints + status polling.
  Defaults to the user wallet token (admin=False); cron-driven
  consumers override.
- `account.journal` becomes the first consumer of both mixins via
  multi-inheritance `_inherit = ["account.journal", <both mixins>]`.

### Changed
- Direct calls to `infopay.provider` from non-core modules are
  formally deprecated — bridges must use the mixin to keep session
  lifecycle consistent.

## 19.0.2.1.0 (2026-05-10)

### Added
- Admin (cron) credentials + dual-key session model:
  - User wallet (password-protected via `l10n_bg_bank_wallet`) — for
    write operations (payments) where the user is present.
  - Admin wallet (Fernet-encrypted in `ir.config_parameter`) — for
    read-only operations (statement sync) running unattended in cron.
  - `infopay.provider._create_session(company, admin=False)` picks
    the right token by flag.

## 19.0.2.0.0 (2026-05-10)

### Added
- Invoice issuance via InfoPay's `/api/invoices` endpoint.  Note: this
  is **not** the regulated e-Faktura.bg B2B exchange — it is InfoPay's
  own invoice-document service.  Used for InfoPay payment-collection
  links, not for НАП reporting.

## 19.0.1.1.0 (2026-03-24)

### Fixed
- Replaced OCA dependency `account_statement_import_base` with Odoo core `account` module
- Removed OCA-specific methods (`_statement_line_import_speeddict`, `_statement_line_import_update_hook`, `_statement_line_import_update_unique_import_id`) from `account_journal.py`
- Fixed `_check_credentials` in `res_users.py` — converted from `@classmethod` to instance method for Odoo 18.0 API compatibility
- Fixed `_infopay_distribute_token` — converted from `@classmethod` to instance method

## 19.0.1.0.0 (2025-03-22)

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
