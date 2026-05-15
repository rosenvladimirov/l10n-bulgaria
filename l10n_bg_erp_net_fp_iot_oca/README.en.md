# ErpNet.FP — OCA IoT bridge (Community)

> CE-friendly bridge between l10n_bg_erp_net_fp and OCA's
        iot_oca module. Auto-installs when both are present.

**Module:** `l10n_bg_erp_net_fp_iot_oca` | **Version:** 18.0.11.0.0 | **License:** LGPL-3 | **Category:** Point Of Sale

## Overview

Drop-in equivalent of `l10n_bg_erp_net_fp_iot` (which depends on the
Enterprise `iot` module) for Community installs that pull in OCA's
`iot_oca` instead. Provides the same end-user features:
* Mirror an `iot.communication.system` (OCA's analogue of EE `iot.box`)
  from a `fiscal.printer.device` — adds `erp_net_fp_url` /
  `erp_net_fp_ssl_verify` fields, plus a one-click "Create matching
  IoT system" header button on the device form
* `iot.device.read_weight()` synchronous helper — calls the ErpNet.FP
  HTTP `/scales/{id}` endpoint and parses the response (no browser
  proxy / bus.bus indirection — the EE bridge needed those because
  EE iot.box assumes the box is in a private network; OCA's flat
  model lets the Odoo backend hit the proxy directly)
* Phase 3 packaging weight QC — abstract weighable mixin + MO /
  picking integration + per-company defaults — identical user flow

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `iot_oca`, `mrp`, `stock` | `l10n_bg_erp_net_fp` |

## New models

- `l10n.bg.packaging.weighable.mixin`
- `mrp.production`
- `stock.picking`

## Extended models

- `fiscal.printer.device` (inherited)
- `iot.communication.system` (inherited)
- `iot.device` (inherited)
- `mrp.bom` (inherited)
- `res.company` (inherited)
- `res.config.settings` (inherited)

## Views

- `views/fiscal_printer_device_iot_oca_bridge_views.xml`
- `views/iot_communication_system_views.xml`
- `views/iot_device_views.xml`
- `views/packaging_qc_views.xml`

## Controllers

- `controllers/main.py`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_erp_net_fp_iot_oca' or via CLI:
odoo -i l10n_bg_erp_net_fp_iot_oca -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
