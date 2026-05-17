# Changelog

All notable changes to the l10n_bg_bank_wallet module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [19.0.1.0.9] - 2026-05-17

### Fixed
- `_create_initial_wallet` now initialises a pre-existing but empty
  "System Keys" wallet (no `encrypted_data`) instead of skipping it.
  Such records were left behind by UI create attempts before 19.0.1.0.8
  and stayed permanently unusable (the "wallet exists but never
  initialised" case).

## [19.0.1.0.8] - 2026-05-17

### Fixed
- **Design bug: wallet never auto-created on modern Odoo.** The module
  keys the wallet with the user's bcrypt password hash
  (`_create_initial_wallet(user_id, hash)`), but obtained it from
  `res.users.password` via the ORM, which in Odoo 17+ is write-only and
  **always reads `False`**. Consequently `_check_credentials` returned
  early on every login (`if not new_password_hash`), so the "System
  Keys" wallet was never created/re-synced and `get_user_master_password`
  always yielded `False` — wallets could not be created or unlocked.
- `crypto.wallet._read_bcrypt_hash()` (new helper): reads the real
  bcrypt hash directly from the `res_users.password` column via SQL by
  the owner-privileged wallet code — the value the design already uses
  as the master password. `get_user_master_password()` now uses it.
- `res.users._check_credentials`: reads the bcrypt hash via SQL (not the
  always-False ORM field) and, on a normal login with no "System Keys"
  wallet, auto-creates it with the bcrypt hash (what `_verify_wallet_sync`
  intended but was never invoked). Re-encryption on password change is
  preserved with the working hash source.

## [19.0.1.0.7] - 2026-05-17

### Fixed
- Wallet creation via UI crashed with `AttributeError: 'bool' object has no
  attribute 'encode'` in `derive_key`. Root cause: `get_user_master_password()`
  returns `user_id.password`, which in Odoo is write-only and **always reads as
  `False`**, so `create()` passed `False` to `_initialize_empty_wallet` →
  `derive_key(False, salt)`. The design intent (master password = user's Odoo
  password, supplied via the unlock wizard) is unchanged.
- `derive_key` now raises a clear `UserError` when password is not a non-empty
  `str` (instead of a cryptic AttributeError / HTTP 500).
- `create()` now fails fast with a clear `UserError` when no usable
  `master_password` is available, before any half-initialised record is made.
  Wallets must be created/unlocked via the wizard (which prompts for the
  password) or with an explicit `master_password` value.

## [19.0.1.0.0] - 2026-04-01

### Changed
- Ported from Odoo 18.0 to Odoo 19.0
- Fixed search view `<group>` element: removed invalid `string` attribute (not allowed in Odoo 19)
- Removed `expand="0"` from search `<group>` (kept for backward compat; Odoo 19 ignores it but does not error)
- Version bump to 19.0.1.0.0

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
