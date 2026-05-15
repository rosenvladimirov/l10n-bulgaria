# Bulgarian Banking Integration - Crypto Wallet

> Secure storage of cryptographic keys and passwords for banking integrations

**Module:** `l10n_bg_bank_wallet` | **Version:** 18.0.1.0.10 | **License:** LGPL-3 | **Category:** Localization

## Overview

Crypto Wallet for Sensitive Data Storage
This module provides a secure way to store:
* RSA keys for digital signing
* API keys for banking integrations
* Passwords and certificates
* Other sensitive cryptographic data
Uses PBKDF2 with 100,000 iterations and Fernet symmetric encryption.
Features:
---------
* **Secure Storage**: All data is encrypted using industry-standard cryptography
* **User Isolation**: Each user has their own wallet accessible only to them
* **Key Management**: Add, retrieve, and manage different types of keys
* **Banking Ready**: Designed specifically for banking API integrations
* **Audit Trail**: Track when keys are accessed and modified

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `web` | — |

**External Python packages:** `cryptography`, `pyzipper`

## New models

- `crypto.wallet`
- `name`

## Extended models

- `res.users` (inherited)

## Views

- `views/l10n_bg_crypto_wallet.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_bank_wallet' or via CLI:
odoo -i l10n_bg_bank_wallet -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
