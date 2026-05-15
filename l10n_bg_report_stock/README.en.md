# L10n Bg Report Stock

> Bulgaria - Accepted delivery documents in stock picking

**Module:** `l10n_bg_report_stock` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** ?

## Overview

Bulgaria - Accepted delivery documents in stock picking

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `stock` | `l10n_bg_report_theme` |

## Extended models

- `stock.move.line` (inherited)

## Reports

- `report/report_accepted_deliveryslip.xml`
- `report/report_handover_protocol.xml`
- `report/stock_report_views.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_report_stock' or via CLI:
odoo -i l10n_bg_report_stock -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
