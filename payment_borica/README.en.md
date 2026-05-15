# Payment Provider: Borica APGW (BG)

> Accept card payments via Borica APGW (CGI v4.0, EMV 3DS 2.x)

**Module:** `payment_borica` | **Version:** 18.0.1.0.0 | **License:** LGPL-3 | **Category:** Accounting/Payment Providers

## Overview

Borica APGW payment provider for Odoo eCommerce, Sales and Invoicing.
Implements the Borica e-Gateway CGI/WWW Forms interface v4.0 with the
MAC_GENERAL signing scheme — accepts bcard, Visa, Mastercard, Diners and
Discover cards through 3-D Secure (EMV 3DS v2.1 / v2.2).
Designed for Bulgarian merchants with a vPOS contract from any of the
local acquirer banks routing through Borica.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `payment`, `website_payment` | — |

## Extended models

- `payment.provider` (inherited)
- `payment.transaction` (inherited)

## Views

- `views/payment_borica_templates.xml`
- `views/payment_provider_views.xml`

## Controllers

- `controllers/main.py`

## Seeded data

- `data/payment_provider_data.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'payment_borica' or via CLI:
odoo -i payment_borica -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)
- Module tests: `tests/`

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
