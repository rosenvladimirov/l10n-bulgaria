# Bulgaria Localization — Configuration Backbone

> The foundation module of the Bulgarian localization. Installs the
> core stack, hides BG-specific UI for non-BG companies, validates
> identifiers, and encrypts API credentials.

**Module:** `l10n_bg_config` | **Version:** 18.0.8.3.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

`l10n_bg_config` is the keystone every other Bulgarian-localization
module depends on. It has three jobs:

1. **One-click localization setup.** Installing it auto-pulls the rest
   of the core stack — `l10n_bg`, `l10n_bg_reports_audit`,
   `l10n_bg_report_theme`, `l10n_bg_ledger`, `l10n_bg_tariff_code` —
   so a fresh database becomes Bulgaria-ready without hunting for
   dependencies.
2. **Multi-company UI discipline.** In a database that mixes Bulgarian
   and non-Bulgarian companies, BG-specific fields and groups would
   clutter every form for the non-BG entities. This module's mixin
   strips them out automatically per active company.
3. **Credential security.** API keys for the NRA / banking
   integrations are never stored in clear text — the module ships the
   XOR+Base64 key derivation used across the localization plus a
   Fernet-encrypted company blacklist.

## Architecture

### `l10n.bg.config.mixin` (AbstractModel)

The heart of the module. Any model that inherits it gains:

- `is_l10n_bg_record` — computed boolean, true when the record's
  company (or the active company) is flagged as Bulgarian via
  `res.company._check_is_l10n_bg_record()`.
- An overridden `get_view()` that, for **non-BG companies**, rewrites
  the returned arch to:
  - set `column_invisible` on every list `<field name="l10n_bg_*">`
  - set `invisible` on every form `<field name="l10n_bg_*">` and any
    `<group>` whose `id`/`name` contains `l10n_bg`
  - hide search filters whose `domain`/`context` references `l10n_bg`

  This means a localization module can add `l10n_bg_*` fields freely;
  they simply vanish for companies that don't need them — no manual
  `invisible` attributes in every view.

### Extended core models

| Model | Why it's extended |
|---|---|
| `res.company` | `_check_is_l10n_bg_record()` gate; BG API key storage |
| `res.partner` | BG UIC (БУЛСТАТ/ЕИК), crypt key, blacklist lookup |
| `account.move` / `account.move.line` | inherit the mixin → auto-hide BG fields for non-BG companies |
| `account.chart.template` | BG chart-of-accounts hook points |
| `account.account.tag` | NRA cell tagging base |
| `res.bank` | `l10n_bg_nap_approved` flag (NAP-approved bank filter) |
| `res.country` | translatable state/region support hooks |
| `ir.module.module` | install-orchestration helpers |

### Credential & blacklist security

- `generate_encryption_keys(key1, key2)` / `decrypt_key(...)` —
  XOR-based key derivation. `is_valid_api_key(uic, api_key,
  crypt_key)` validates the NRA submission credential triple without a
  direct equality check (digest folding to obscure intent).
- `prepare_zip_payload()` — wraps NRA report files; injects a random
  one-time password when the company's API-key triple is invalid, so
  exports degrade safely instead of leaking.
- **Blacklist:** `data/blacklist.enc` is a Fernet-encrypted file;
  controller `/l10n_bg/blacklist/check` decrypts it with the key from
  `ir.config_parameter`. An OWL service shows a sticky warning when a
  loaded company is blacklisted and a non-dismissable overlay if the
  security file is missing/corrupted. *(As of 18.0.8.2.1 the JS
  service is short-circuited in `start()`; controller + file + bus
  channel remain — re-enable by removing the early return in
  `static/src/services/blacklist_service.js`.)*

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `account`, `base_vat` | `l10n_bg`, `l10n_bg_ledger`, `l10n_bg_tariff_code` |

**External Python:** `xmltodict`, `cryptography` (Fernet).

## Configuration

1. Apps → search **l10n_bg_config** → Install (dependencies auto-install).
2. Settings → Localization → Bulgarian Localization → review enabled modules.
3. Set the company's БУЛСТАТ/ЕИК and NRA API credentials on the company
   partner; the module derives and stores the encrypted crypt key.
4. If using the blacklist: set the Fernet key in `ir.config_parameter`
   and manage entries via `tools/update_blacklist.py`.

## Field-naming convention enforced ecosystem-wide

Any field a localization module adds to an Odoo core model
(`account.move`, `res.partner`, `res.company`, `pos.*`, …) **must** be
prefixed `l10n_bg_`. The mixin's view rewriting depends on this prefix
to find and hide fields — non-prefixed fields will leak into non-BG
company forms.

## Known limitations

- Blacklist JS UI disabled by default since 18.0.8.2.1 (backend pieces intact).
- `get_view` arch rewriting is per-call; very large views add minor parse overhead for non-BG companies.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Cross-repo map: `claude.ai/L10N_BG_ECOSYSTEM.md`
- `readme/` — DESCRIPTION / CONTEXT / CONFIGURE source notes
- Downstream consumers: virtually every `l10n_bg_*` module

## License validation & data (important)

On installation this module registers the installation for **license validation**:
a minimal record is sent to the vendor server — the **UIC (ЕИК) and name of the MAIN
company**, a database identifier, and which paid (Enterprise) modules are installed.
This is used solely to verify license entitlements for the paid modules. Additional
companies in a multi-company database are NOT sent.

Opt-out: system parameter `l10n_bg.register_enabled = 0`.
