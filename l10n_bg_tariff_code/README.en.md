# Bulgaria Tariff Code Management

> TARIC/HS/CN Code Management with EU API Integration

**Module:** `l10n_bg_tariff_code` | **Version:** 18.0.3.0.11 | **License:** LGPL-3 | **Category:** Accounting/Localizations

## Overview

Bulgaria Tariff Code Management
This module provides comprehensive tariff code management for Bulgarian companies.
TARIC Integration
-----------------
* Automatic TARIC code detection from HS/CN/Intrastat codes
* Real-time tariff rate lookup from EU TARIC API system
* Caching mechanism for tariff rates
* Support for multiple countries of origin
* Backward compatibility with HS/CN codes
Product Extensions
------------------
* Tariff code management on products
* Automatic HS code synchronization
* Country of origin tracking

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `account`, `stock_delivery` | — |

**External Python packages:** `requests`

## New models

- `cn_code`
- `l10n_bg.taric.cache`

## Extended models

- `account.move.line` (inherited)
- `product.product` (inherited)
- `product.template` (inherited)
- `res.company` (inherited)
- `res.config.settings` (inherited)

## Views

- `views/account_move_line_views.xml`
- `views/l10n_bg_taric_cache.xml`
- `views/menu.xml`
- `views/product_template_views.xml`
- `views/res_config_view.xml`

## Seeded data

- `data/l10n_bg_tarif_code_data.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_tariff_code' or via CLI:
odoo -i l10n_bg_tariff_code -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
