# ErpNet.FP Fiscal Printer for odoo

> Integration with ERP.BG fiscal printers through ErpNet.FP server.
        Supports real-time fiscal receipt printing and status monitoring.

**Module:** `l10n_bg_erp_net_fp` | **Version:** 18.0.15.1.0 | **License:** LGPL-3 | **Category:** Point Of Sale

## Overview

This module provides integration between Odoo POS and fiscal printers
supported by ErpNet.FP server. Features include:
* Real-time fiscal receipt printing from POS
* Direct browser-to-printer communication for receipts
* Backend support for Z/X reports and administrative operations
* Printer status monitoring
* Automatic fallback to standard printing on error
* Multiple printer support
* Background printer status updates
* Detailed error logging
* Support for different printer models
* Bulgarian tax group mapping (А, Б, В, Г)
* Dual connection mode: Direct (server) and Proxy (browser)

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `bus`, `mail`, `point_of_sale`, `account` | — |

## New models

- `fiscal.frame.log`
- `fiscal.printer.device`
- `fiscal.printer.response`
- `fiscal.printer.status`
- `fiscal.session`
- `l10n.bg.fiscal.plu`
- `l10n.bg.fiscal.shift`
- `l10n.bg.fiscal.shift.receipt`
- `l10n.bg.fiscal.shift.receipt.line`
- `l10n.bg.fiscal.z.report`
- `receipt_number`
- `request_id`
- `summary`

## Extended models

- `account.tax.group` (inherited)
- `fiscal.printer.device` (inherited)
- `pos.config` (inherited)
- `pos.order` (inherited)
- `pos.payment.method` (inherited)
- `pos.printer` (inherited)
- `pos.session` (inherited)
- `product.pricelist` (inherited)
- `product.pricelist.item` (inherited)
- `product.product` (inherited)
- `product.template` (inherited)
- `res.config.settings` (inherited)
- `res.users` (inherited)

## Views

- `views/account_tax_views.xml`
- `views/external_shift_layout.xml`
- `views/fiscal_frame_log_views.xml`
- `views/fiscal_plu_views.xml`
- `views/fiscal_printer_device_proxy_views.xml`
- `views/fiscal_printer_device_views.xml`
- `views/fiscal_printer_response_views.xml`
- `views/fiscal_session_views.xml`
- `views/fiscal_shift_receipt_views.xml`
- `views/fiscal_shift_views.xml`
- `views/fiscal_z_report_views.xml`
- `views/grafana_settings_views.xml`
- `views/grafana_views.xml`
- `views/menu_items.xml`
- `views/menu_items_proxy.xml`
- `views/pos_config_proxy_views.xml`
- `views/pos_config_view.xml`
- `views/pos_order_view.xml`
- `views/pos_payment_method_proxy_views.xml`
- `views/pos_printer_views.xml`
- `views/pos_session_view.xml`
- `views/product_template_proxy_views.xml`
- `views/res_config_settings_views.xml`
- `views/res_users_views.xml`

## Wizards

- `wizard/fiscal_cash_operation_wizard.py`
- `wizard/plu_allocate_wizard.py`
- `wizard/plu_push_wizard.py`
- `wizard/plu_topn_wizard.py`
- `wizard/x_report_wizard.py`

## Controllers

- `controllers/external_shift.py`
- `controllers/main.py`

## Seeded data

- `data/fiscal_printer_device_cron.xml`
- `data/proxy_sequences.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_erp_net_fp' or via CLI:
odoo -i l10n_bg_erp_net_fp -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
