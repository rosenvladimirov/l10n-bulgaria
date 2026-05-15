# ErpNet.FP Fleet Manager

> Central control plane for distributed ErpNet.FP proxy instances.

**Module:** `l10n_bg_erp_net_fp_fleet` | **Version:** 18.0.1.0.0 | **License:** LGPL-3 | **Category:** Hardware/Fleet

## Overview

Fleet manager for ErpNet.FP fiscal-printer proxies. Each proxy
deployed in a shop heartbeats here every minute with version, host,
and the list of attached devices (printers, pinpads, scales, readers,
displays). Administrators can:
* Generate one-time pairing tokens to enrol new proxies
* Monitor `last_seen` and computed `alive` status
* Trigger remote `/admin/self-update` with one click
* Stream `/admin/logs` from the proxy without shell access
* Program fiscal-printer VAT rates remotely
The proxy's admin token is stored Fernet-encrypted at rest with a
key kept in `ir.config_parameter` (visible only to base.group_system).
This module has NO dependency on `point_of_sale`, `iot`, `mrp`, or
`stock` and is designed to run on a dedicated CE Odoo instance
(default `iot.mcpworks.net`) — the central registry need not also

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `mail` | — |

**External Python packages:** `cryptography`

## New models

- `erpnet.fp.fernet`
- `erpnet.fp.proxy`
- `name`

## Views

- `views/erpnet_fp_proxy_views.xml`
- `views/menu_items.xml`

## Wizards

- `wizard/erpnet_fp_program_vat_wizard.py`

## Controllers

- `controllers/registry.py`

## Seeded data

- `data/ir_config_parameter.xml`
- `data/ir_cron.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_erp_net_fp_fleet' or via CLI:
odoo -i l10n_bg_erp_net_fp_fleet -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
