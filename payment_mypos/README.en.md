# Payment Provider — myPOS Checkout

> Accept card payments via the myPOS Checkout API (REST + 3DS):
> hosted-redirect purchase plus refund/void.

**Module:** `payment_mypos` | **Version:** 18.0.2.0.0 | **License:** LGPL-3 | **Category:** Localization / Payment

## Overview

myPOS is a pan-European merchant-acquiring provider popular with
Bulgarian SMBs (its hardware is shared lineage with Datecs). This
module adds myPOS as an Odoo `payment.provider` using the **myPOS
Checkout API v1.4.1** — the hosted-redirect purchase flow
(`IPCPurchase`) for payment, plus `IPCRefund` / `IPCVoid` for
post-payment operations.

## Architecture

- `payment.provider` — myPOS provider with the Checkout credentials.
  Refund/void require additional credentials (set on the provider) —
  mandatory for `IPCRefund` / `IPCVoid` under Checkout API v1.4.1.
- Purchase: hosted-redirect (`IPCPurchase`) with 3-D Secure.
- Refund/Void: server-to-server REST calls keyed by the original
  transaction.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `payment` | `l10n_bg` |

## Configuration

1. Invoicing → Payment Providers → myPOS → enter the Checkout
   store/keys; add the refund/void credentials if you need
   server-side reversals.
2. Set test/production; enable on website/invoice flows.

## AUP / compliance constraints

Per the myPOS Acceptable Use Policy: card PAN/PIN/CVV must never be
logged or stored; refunds only to the original card; chargeback rate
must stay < 1%; pre-auth is allowed only for hotel / cruise /
rent-a-car. See
`claude.ai/memory/reference_mypos_acceptable_use_policy.md`.

## Strategic note

myPOS + Borica are the primary card providers for the localization
(EU focus, LGPL-3). See
`claude.ai/memory/project_payment_provider_strategy.md`.

## Known limitations

- Refund/void need the extra Checkout credentials configured;
  otherwise only purchase works.
- Hosted-redirect UX is myPOS-controlled.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Sibling provider: `payment_borica`
- AUP: `claude.ai/memory/reference_mypos_acceptable_use_policy.md`
