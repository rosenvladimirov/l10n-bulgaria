# Bulgaria — Encrypted Crypto Wallet

> Per-user encrypted vault for the cryptographic material that the
> banking + NRA integrations need: RSA keys, API tokens, passwords,
> certificates. Encrypted at rest, unlocked only after authentication.

**Module:** `l10n_bg_bank_wallet` | **Version:** 18.0.1.0.10 | **License:** LGPL-3 | **Category:** Localization

## Overview

Bulgarian banking (InfoPay, Borica) and NRA submission flows require
private signing keys, access tokens and passwords. Storing those in
clear-text fields would be a critical exposure. `l10n_bg_bank_wallet`
provides a `crypto.wallet` model where every secret is encrypted at
rest and only decryptable by the owning user after they authenticate
— the wallet key is derived from the user's own Odoo password hash, so
an admin reading the database still cannot read another user's keys.

It sits at the very bottom of the dependency graph (`base`, `web`
only) so any integration module can rely on it.

## Cryptography

| Layer | Algorithm |
|---|---|
| Key derivation | **PBKDF2-HMAC-SHA256**, 100 000 iterations, per-wallet random salt |
| Symmetric encryption | **Fernet** (AES-256 in GCM, authenticated) |
| At-rest storage | Encrypted blobs in `filestore/crypto_wallets/<db>/` — not in the DB |
| Key scope | Derived from the user's Odoo password hash → per-user isolation |

Static helpers: `generate_salt()`, `derive_key(password, salt)`,
`encrypt_data(data, key)`, `decrypt_data(blob, key)`,
`create_wallet_envelope(...)`.

## Data model

### `crypto.wallet`

- Per-user wallet (`res.users.crypto_wallet_ids` One2many).
- `unlock_wallet_with_password()` / `lock_wallet()` — session-scoped
  unlock; encryption key held only in session state, never persisted.
- `add_key_with_user_password(name, type, data)` /
  `get_key_with_user_password(name)` — store/retrieve a secret.
- `quick_store(name, type, data)` / `quick_access(name)` — convenience
  one-liners used across the localization.
- `generate_keypair(name, key_type='rsa'|'ec')` — creates
  `<name>_private` + `<name>_public` entries in-wallet.
- Disk persistence: `_persist_wallet_to_disk()` /
  `_load_wallet_from_disk()` with filename obfuscation
  (`generate_wallet_filename`).

### `res.users` (extended)

On password change, wallets are **automatically re-encrypted**:
`_handle_wallet_reencryption(old_hash, new_hash)` →
`auto_reencrypt_on_password_change(...)`, plus `_verify_wallet_sync`
to detect drift. A password change therefore never orphans the user's
stored keys.

## Permission model

Five security groups gate operations:

| Group | Allows |
|---|---|
| `group_crypto_wallet_read` | read decrypted values |
| `group_crypto_wallet_write` | add/update keys |
| `group_crypto_wallet_admin` | manage all wallets |
| `group_crypto_wallet_generate` | generate keypairs |
| `group_crypto_wallet_export` | export key material |

`check_access(operation)` + `_validate_record_access()` enforce these.

## Wizards

- Add Key (`crypto_wallet_add_key_wizard`)
- Unlock Wallet (`crypto_wallet_unlock_wizard`)
- Change Password (`crypto_wallet_change_password_wizard`)

## Usage

```python
# store
w = env['crypto.wallet'].get_user_wallet_or_create()
w.add_key_with_user_password('infopay_token', 'api_key', 'secret')

# retrieve
w = env['crypto.wallet'].get_user_wallet()
val = w.get_key_with_user_password('infopay_token')['data']

# quick helpers
CW = env['crypto.wallet']
CW.quick_store('token', 'api_key', 'abc123')
CW.quick_access('token')

# keypair
w.generate_keypair('signing', key_type='rsa')
```

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `base`, `web` | — (foundational; no l10n deps) |

**External Python:** `cryptography`.

## Downstream consumers

`l10n_bg_api_nra` (NRA access token), `l10n_bg_infopay` + EE/OCA
bridges (Borica InfoPay credentials), any module needing signed
payloads.

## Known limitations

- Wallet unlock is session-scoped; long idle sessions re-prompt.
- Losing the Odoo password without the change-password flow (e.g.
  admin reset bypassing `res.users` hook) can strand wallet contents
  — use the Change Password wizard, not a raw admin reset.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- `readme/` — DESCRIPTION / INSTALL / USAGE source notes
- Consumer: `l10n_bg_api_nra` (token sharing pattern)
