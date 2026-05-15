# ErpNet.FP Fleet Manager

> Central control plane for distributed ErpNet.FP proxy instances:
> HMAC-signed heartbeat enrolment, Fernet-encrypted shared secrets,
> pairing tokens and a command queue.

**Module:** `l10n_bg_erp_net_fp_fleet` | **Version:** 18.0.1.0.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

A merchant with many sites runs many ErpNet.FP proxy instances (one
per location, near the fiscal devices). This module is the **central
registry + control plane**: proxies enrol themselves, send HMAC-signed
heartbeats, and receive commands via a queue — so an operator manages
the whole fleet from one Odoo instance instead of touching each box.

## Architecture

- **Enrolment**: public-facing registry endpoints; a proxy enrols with
  a pairing token, then a long-lived shared secret is issued.
- **Heartbeats**: the proxy sends periodic heartbeats whose body is
  HMAC-signed with its shared secret; the server validates the HMAC
  to authenticate the proxy.
- **Secret storage**: shared secrets are **Fernet-encrypted at rest**
  (AES-128-CBC + HMAC-SHA256) with the key in `ir.config_parameter`
  `l10n_bg_erp_net_fp_fleet.fernet_key` (auto-created;
  `erpnet.fp.fernet` model does encrypt/decrypt). A DB-backup leak
  alone does not expose fleet secrets.
- **Lifecycle actions**: `action_generate_pairing_token`,
  `action_reset_secret`, `action_archive_proxy`.
- **Command queue**: pull-model — proxies poll for queued commands and
  report completion.

## Dependencies

| Odoo core | Bulgarian-localization | External Python |
|---|---|---|
| `base`, `mail` | — (control plane; pairs with `l10n_bg_erp_net_fp` on the proxy side) | `cryptography` |

## Configuration

1. Install; the Fernet key auto-generates on first use.
2. Generate a pairing token per proxy → configure the proxy with it.
3. The proxy enrols, receives its secret, and begins HMAC heartbeats;
   manage it from the fleet view (reset secret / archive as needed).

## Known limitations

- HMAC validation iterates candidate secrets — noted as slow at very
  large fleet scale (acceptable for typical merchant fleets).
- This is the server side; the proxy side lives in the ErpNet.FP
  deployment, not in Odoo.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Device integration: `l10n_bg_erp_net_fp`
