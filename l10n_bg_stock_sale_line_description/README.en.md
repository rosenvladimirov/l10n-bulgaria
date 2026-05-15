# Stock Sale Line Description

> Show sale order line description on pickings and delivery slips

**Module:** `l10n_bg_stock_sale_line_description` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** ?

## Overview

Show sale order line description on pickings and delivery slips

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `stock`, `sale_stock` | — |

## Extended models

- `stock.move` (inherited)

## Views

- `views/stock_picking_views.xml`

## Reports

- `report/report_deliveryslip.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_stock_sale_line_description' or via CLI:
odoo -i l10n_bg_stock_sale_line_description -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
