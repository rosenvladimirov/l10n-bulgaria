# Changelog

All notable changes to the l10n_bg_bank_wallet module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
