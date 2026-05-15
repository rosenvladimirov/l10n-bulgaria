# Bulgarian Sale Order Delivery Note

> Generate Accepted Delivery Report for Bulgarian Sale Orders

**Module:** `l10n_bg_sale_order_delivery_note` | **Version:** 18.0.1.1.1 | **License:** LGPL-3 | **Category:** Sales/Bulgaria

## Overview

Bulgarian Sale Order Delivery Note
       ==================================
       This module generates "Accepted Delivery Report" (Приемо-предавателен протокол)
       for sale orders in Bulgaria.
       It creates a specialized report template for delivery confirmation documents
       according to Bulgarian business practices.
       Features:
       ---------
       * Generates Accepted Delivery Report for sale orders
       * Bulgarian localization for delivery documentation
       * Compatible with Bulgarian report theme
       * Pro-forma delivery note template

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `sale`, `base_comment_template` | `l10n_bg_report_theme` |

## New models

- `sale.order`

## Reports

- `report/ir_action_report_templates.xml`
- `report/ir_actions_report.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_sale_order_delivery_note' or via CLI:
odoo -i l10n_bg_sale_order_delivery_note -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
