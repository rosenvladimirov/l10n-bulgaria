# Payment Provider: myPOS

> Accept card payments via myPOS Checkout API (REST + 3DS)

**Module:** `payment_mypos` | **Version:** 18.0.1.2.0 | **License:** LGPL-3 | **Category:** Accounting/Payment Providers

## Overview

myPOS payment provider for Odoo eCommerce, Sales and Invoicing.
Integrates the myPOS Checkout API v1.4.1 — accepts Visa, Mastercard, JCB,
Bancontact and other supported card schemes through 3D Secure flows.
Designed for use in 30+ EU countries where myPOS operates.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `payment`, `website_payment` | — |

## Extended models

- `payment.provider` (inherited)
- `payment.transaction` (inherited)

## Views

- `views/payment_mypos_templates.xml`
- `views/payment_provider_views.xml`

## Controllers

- `controllers/main.py`

## Seeded data

- `data/payment_provider_data.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'payment_mypos' or via CLI:
odoo -i payment_mypos -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)
- Module tests: `tests/`

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
