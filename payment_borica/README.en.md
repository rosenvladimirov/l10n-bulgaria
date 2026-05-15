# Payment Provider — Borica APGW

> Accept card payments through the Borica e-commerce gateway (APGW,
> CGI v4.0, EMV 3-D Secure 2.x) — a Bulgarian-bank-issued acquiring
> channel.

**Module:** `payment_borica` | **Version:** 18.0.1.0.0 | **License:** LGPL-3 | **Category:** Localization / Payment

## Overview

Borica is the Bulgarian national card operator; its **APGW**
(e-commerce gateway) is the acquiring channel most Bulgarian banks
issue to merchants. This module adds Borica as an Odoo
`payment.provider` so web-shop / invoice payments route through the
bank's gateway with full EMV 3-D Secure 2.x cardholder authentication.

## Architecture

- `payment.provider` — `provider` selection extended with
  `("borica", "Borica APGW")`; carries the merchant's terminal/
  acquirer credentials.
- CGI v4.0 request signing + the 3DS 2.x redirect flow.
- `_process_notification_data(notification_data)` — verifies the
  signed gateway callback and reconciles the transaction state
  (authorised / declined / cancelled).

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `payment` | `l10n_bg` |

## Configuration

1. Invoicing → Payment Providers → Borica APGW → enter the
   bank-issued terminal ID / acquirer credentials, set test/production.
2. Enable on the website / invoice payment flows.
3. Verify the gateway callback URL is reachable from Borica.

## Strategic note

Borica + myPOS are the primary card-acceptance providers for the
Bulgarian localization (LGPL-3, EU focus). See
`claude.ai/memory/project_payment_provider_strategy.md`.

## Known limitations

- Requires a Borica merchant agreement via a Bulgarian bank
  (terminal/acquirer credentials are bank-issued).
- 3DS challenge UX depends on the cardholder's issuing bank.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Sibling provider: `payment_mypos`
- Strategy: `claude.ai/memory/project_payment_provider_strategy.md`
