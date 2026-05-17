# Changelog

All notable changes to the l10n_bg_bank_wallet module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.1.1.0] - 2026-05-17

### Fixed
- Backport of the 19.0.1.0.7–19.0.1.1.1 wallet-lifecycle fix chain (all
  six bugs were present identically on 18.0). The Odoo `api.Environment`
  refactor that makes `context`/`cr`/`uid`/`su` **read-only landed in
  Odoo 18.0**, so every item — including the `env.context` one — applies.
  - `derive_key`: clear `UserError` instead of `bool.encode()` 500.
  - `_read_bcrypt_hash()` (new) + `get_user_master_password()`: read the
    bcrypt hash from `res_users.password` via SQL (the ORM field is
    write-only/`False` on Odoo 17+).
  - `res.users._check_credentials`: SQL bcrypt hash + auto-create the
    "System Keys" wallet on normal login; `_create_initial_wallet`
    initialises a pre-existing empty wallet instead of skipping it.
  - `_check_permission_level` / `_validate_record_access`: `env.su`
    bypass so the module's own sudo'd lifecycle is not blocked.
  - Removed the illegal `self.env.context = ...` key cache (read-only on
    Odoo 18/19); key derived statelessly via `_derive_active_key`.
  Verified end-to-end on the 19.0 twin (create→init→unlock→import→
  readback, InfoPay 4 keys). Bulgarian `help=` string on
  `crypto_wallet_ids` kept as-is (grandfathered; the 19.0 i18n sweep was
  deliberately not bundled into this lifecycle backport).

## [18.0.1.0.5] - 2026-03-24

### Fixed
- Fixed audit rule domain: `datetime.datetime.now()` not available in XML eval context, replaced with `datetime.date.today()`

## [18.0.1.0.4] - 2026-03-24

### Fixed
- Fixed `_create_initial_wallet` creating duplicate "System Keys" wallets on every login — now checks for existing wallet before creating

## [18.0.1.0.3] - 2026-03-24

### Fixed
- Fixed `_check_credentials` TypeError: was `@classmethod` with `(cls, env, credential)` signature, but Odoo 18.0 expects instance method `(self, credential, user_agent_env)` — caused login failure after module installation
- Converted all helper methods (`_handle_wallet_reencryption`, `_verify_wallet_sync`, `_create_initial_wallet`) from `@classmethod` to instance methods using `self.env`

## [18.0.1.0.2] - 2026-03-22

### Fixed
- Added missing `auto_reencrypt_on_password_change()` method on `crypto.wallet`
- Added missing `_create_initial_wallet()` classmethod on `res.users`
- Fixed `unlock_wallet()` → `unlock_wallet_with_password()` call in `res_users.py`
- Fixed bare `except:` clauses → `except Exception:` (res_users, crypto_wallet, unlock wizard)
- Fixed `self._crypto_manager` → `self.crypto_manager` property access in `_initialize_empty_wallet`
- Fixed `_check_permission_level` called on empty recordset in `@api.model` methods
- Fixed `create()` calling `_check_permission_level` on empty recordset
- Fixed invalid `time.time()` in audit rule domain → `datetime` expression
- Changed license from AGPL-3 to LGPL-3

## [18.0.1.0.1] - 2026-03-01

### Added
- Initial changelog entry
