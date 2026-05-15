# Bulgaria — NRA API Integration (core)

> The submission backbone for filing declarations to the Bulgarian
> National Revenue Agency (НАП) over its public API, with qualified
> electronic-signature (КЕП) signing in the browser.

**Module:** `l10n_bg_api_nra` | **Version:** 18.0.1.4.2 | **License:** LGPL-3 | **Category:** Accounting/Localizations | **Application:** Yes (standalone NRA app)

## Overview

`l10n_bg_api_nra` is the transport + signing core that every
declaration-specific module (D1, D6, VAT, VIES, ETZ, Naredba H-18
e-shop) builds on. It owns the HTTP client, the test/production
endpoint switch, the wallet-backed access-token sharing, and the
client-side КЕП signing dialog. Declaration content/format lives in
the sibling `l10n_bg_api_nra_*` and `l10n_bg_hr_payroll_nra_*`
modules; this module gets the signed payload to НАП and back.

It is registered as a **standalone Odoo application** (its own root
menu + NAP vector icon) rather than buried under Accounting.

## Architecture

### `nra.api.provider`

The raw HTTP client.

- `_get_base_url()` — reads `ir.config_parameter`
  `l10n_bg_api_nra.base_url` (falls back to the built-in NRA API base).
- `_get_submit_endpoint(company)` — resolves the full submit URL based
  on the company's **test vs production** mode, so the same code path
  exercises the НАП sandbox or live without edits.
- Endpoint path constants are appended to the resolved base.

### `nra.declaration` (abstract parent) + concrete declarations

| Model | Declaration |
|---|---|
| `nra.declaration` | shared state machine + submit/poll plumbing |
| `nra.declaration.d1` (+ `.d1.line`) | Декларация Образец 1 |
| `nra.declaration.d6` (+ `.d6.line`) | Декларация Образец 6 |
| `nra.declaration.vat` (+ `.vat.line`) | ДДС declaration |
| `nra.declaration.vies` | VIES declaration |
| `nra.declaration.h18_eshop` (+ `.h18.line`, `.h18.line.art`, `.h18.refund`) | Наредба Н-18 e-shop sales register (`action_collect_h18_orders`, `action_h18_generate_xml`) |

XSD schemas ship under `data/xsd/` and validate payloads before submission.

### Wallet-backed token sharing (`res.users`)

NRA access tokens are not stored per-user in clear text. The token
**owner** (`company.l10n_bg_nra_token_user_id`) holds the
`nra_access_token` key in their `l10n_bg_bank_wallet`. When another
user submits, the module copies the key from the owner's wallet into
the acting user's wallet (skipping if the user *is* the owner, and
purging stale keys first). This means a team can file declarations
without each member holding raw credentials.

### Client-side КЕП signing

`static/src/js/kep_signer.js` + `sign_submit_dialog.js` +
`sign_submit_widget.js` (+ QWeb `sign_submit_dialog.xml`) implement
the qualified-electronic-signature flow **in the browser** — the
private key never leaves the client. `controllers/main.py` handles the
sign/submit round-trip endpoints.

### Extended models

| Model | Addition |
|---|---|
| `res.company` | `l10n_bg_nra_token_user_id` (token owner) + test/prod mode |
| `res.users` | wallet token-copy logic on submit |
| `hr.employee` | `_l10n_bg_nra_declaration_lookups`, `action_view_l10n_bg_nra_declarations` |

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| (accounting/HR base) | `l10n_bg_config`, `l10n_bg_bank_wallet` |

`l10n_bg_bank_wallet` is mandatory — it is where the encrypted NRA
access token lives.

## Configuration

1. Install (registers the NRA application + icon).
2. Settings → set the company's test/production NRA mode and
   `l10n_bg_nra_token_user_id` (the credential owner).
3. The token owner authenticates once; their wallet stores the access
   token. Other users inherit it transparently on submit.
4. (Optional) override `l10n_bg_api_nra.base_url` in
   `ir.config_parameter` to point at a custom/sandbox gateway.

## Downstream consumers

`l10n_bg_api_nra_dec1`, `_dec6`, `_etz`, `_vat`, `_noi*`,
`l10n_bg_hr_payroll_nra_*`, `l10n_bg_account_nra_vat` — all delegate
transport + signing here.

## Known limitations

- Token sharing assumes one credential owner per company; multi-owner
  rotation is manual.
- КЕП signing requires the browser-side signing extension/driver on
  the client machine.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- NRA form formats: `claude.ai/memory/reference_nra_obr55_okd5_formats.md`
- Cross-repo map: `claude.ai/L10N_BG_ECOSYSTEM.md`
