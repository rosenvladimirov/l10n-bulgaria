# България — Криптиран Crypto Wallet

> Per-user криптиран трезор за криптографския материал, нужен на
> банковите + НАП интеграции: RSA ключове, API токени, пароли,
> сертификати. Криптиран at rest, отключван само след автентикация.

**Модул:** `l10n_bg_bank_wallet` | **Версия:** 18.0.1.0.10 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

Българското банкиране (InfoPay, Borica) и НАП submission flow-овете
изискват частни signing ключове, access токени и пароли.
Съхраняването им в clear-text полета би било критична експозиция.
`l10n_bg_bank_wallet` предоставя модел `crypto.wallet`, в който всяка
тайна е криптирана at rest и декриптируема само от притежаващия
потребител след автентикация — wallet ключът се деривира от
собствения Odoo password hash на потребителя, така че админ, четящ
базата, пак не може да чете чужди ключове.

Стои в самото дъно на графа зависимости (само `base`, `web`), за да
може всеки интеграционен модул да разчита на него.

## Криптография

| Слой | Алгоритъм |
|---|---|
| Деривация на ключ | **PBKDF2-HMAC-SHA256**, 100 000 итерации, per-wallet случаен salt |
| Симетрично криптиране | **Fernet** (AES-256 GCM, authenticated) |
| At-rest съхранение | Криптирани blob-ове в `filestore/crypto_wallets/<db>/` — не в БД |
| Обхват на ключа | Деривиран от Odoo password hash на потребителя → per-user изолация |

Статични помощници: `generate_salt()`, `derive_key(password, salt)`,
`encrypt_data(data, key)`, `decrypt_data(blob, key)`,
`create_wallet_envelope(...)`.

## Модел на данните

### `crypto.wallet`

- Per-user wallet (`res.users.crypto_wallet_ids` One2many).
- `unlock_wallet_with_password()` / `lock_wallet()` — session-scoped
  отключване; encryption ключът се държи само в session state, никога
  не се persist-ва.
- `add_key_with_user_password(name, type, data)` /
  `get_key_with_user_password(name)` — store/retrieve на тайна.
- `quick_store(name, type, data)` / `quick_access(name)` — convenience
  едноредови, ползвани в цялата локализация.
- `generate_keypair(name, key_type='rsa'|'ec')` — създава
  `<name>_private` + `<name>_public` записи в wallet-а.
- Disk persistence: `_persist_wallet_to_disk()` /
  `_load_wallet_from_disk()` с filename обфускация
  (`generate_wallet_filename`).

### `res.users` (разширен)

При смяна на парола wallet-ите се **автоматично пре-криптират**:
`_handle_wallet_reencryption(old_hash, new_hash)` →
`auto_reencrypt_on_password_change(...)`, плюс `_verify_wallet_sync`
за откриване на drift. Смяна на парола следователно никога не
orphan-ва съхранените ключове на потребителя.

## Модел на правата

Пет security групи gate-ват операциите:

| Група | Позволява |
|---|---|
| `group_crypto_wallet_read` | четене на декриптирани стойности |
| `group_crypto_wallet_write` | добавяне/обновяване на ключове |
| `group_crypto_wallet_admin` | управление на всички wallet-и |
| `group_crypto_wallet_generate` | генериране на keypairs |
| `group_crypto_wallet_export` | експорт на key material |

`check_access(operation)` + `_validate_record_access()` ги налагат.

## Помощници (wizards)

- Add Key (`crypto_wallet_add_key_wizard`)
- Unlock Wallet (`crypto_wallet_unlock_wizard`)
- Change Password (`crypto_wallet_change_password_wizard`)

## Употреба

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

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `base`, `web` | — (фундаментален; без l10n зависимости) |

**Python пакети:** `cryptography`.

## Downstream consumers

`l10n_bg_api_nra` (НАП access token), `l10n_bg_infopay` + EE/OCA
bridges (Borica InfoPay credentials), всеки модул нуждаещ се от
подписани payloads.

## Известни ограничения

- Wallet отключването е session-scoped; дълги idle сесии re-prompt-ват.
- Загуба на Odoo паролата без change-password flow (напр. админ reset,
  заобикалящ `res.users` hook) може да заключи съдържанието на
  wallet-а — ползвайте Change Password wizard, не суров админ reset.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- `readme/` — DESCRIPTION / INSTALL / USAGE изходни бележки
- Consumer: `l10n_bg_api_nra` (token sharing pattern)
