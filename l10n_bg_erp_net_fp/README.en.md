# Bulgaria — ErpNet.FP Fiscal Printers

> Browser-to-printer fiscal-receipt printing for Bulgarian POS via the
> ErpNet.FP server, with PLU management, external-POS shift handling,
> and a standalone shift dashboard.

**Module:** `l10n_bg_erp_net_fp` | **Version:** 18.0.15.1.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

Bulgarian law requires fiscal receipts from a registered fiscal device.
This module connects Odoo POS to Bulgarian fiscal printers through the
**ErpNet.FP** server: the receipt is printed **directly from the
browser to the device**, bypassing backend bottlenecks, while the
backend still drives administrative operations (Z/X reports, cash
in/out). Bulgarian tax groups (А, Б, В, Г) are mapped automatically,
and printing falls back to a standard receipt on device error so a
sale is never blocked.

## Data model (key entities)

| Model | Role |
|---|---|
| `fiscal.printer.device` | A registered ErpNet.FP device + its status |
| `fiscal.printer.status` / `.status.history` | Live + historical device health (`action_request_status`, cleanup, history view) |
| `fiscal.printer.response` | Per-request response log (keyed by `request_id`) |
| `fiscal.frame.log` | Raw fiscal-frame request/response audit trail |
| `fiscal.plu` | **PLU (Price Look-Up)** items — name+price snapshot synced from the POS pricelist; consistency check before push |
| `fiscal.shift` / `.shift.receipt` | External-POS-mode shift + its receipts |
| `fiscal.z.report` | Z-report record (`action_test_z_report`, close) |
| `fiscal.session` | Z-cycle session marker |

### PLU handling

`fiscal.plu` mirrors POS pricelist items into device memory.
`action_check_consistency` / `action_sync_from_pricelist` /
`action_push_to_device` keep device PLUs aligned; `_next_free_plu`
allocates slots (max ~10000). A mid-shift price change marks the PLU
stale → re-pushed at next shift open (see
`claude.ai/memory/reference_fiscal_plu_concept.md`).

### External POS mode

For setups where sales originate outside a standard `pos.session`
(`fiscal_printer_device_external`, `pos_session_external`):
`action_pos_session_open`, `action_pos_session_closing_control`,
`_l10n_bg_import_receipts`, `action_l10n_bg_external_push_retry`,
`action_l10n_bg_external_force_close`. A **standalone OWL dashboard**
is served at the `/external-shift` route (own asset bundle +
`controllers/external_shift.py`).

### POS / product extensions

`pos.config`, `pos.order`, `pos.session`, `pos.payment.method`,
`pos.printer` extended for fiscal flow; `product.template/product` +
`product.pricelist` extended for PLU linkage; `account.tax.group`
mapped to А/Б/В/Г.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `point_of_sale` (+ account) | `l10n_bg` |

## Configuration

1. Stand up an ErpNet.FP server reachable from the cashier browsers.
2. Settings → register `fiscal.printer.device` entries (host/port).
3. Map POS configs to devices; verify А/Б/В/Г tax-group mapping.
4. Sync PLUs from the pricelist and push to the device.
5. For external mode: use the `/external-shift` dashboard.

## Sister modules

- `l10n_bg_erp_net_fp_fleet` — central fleet manager for many ErpNet.FP instances
- `l10n_bg_erp_net_fp_iot_oca` (CE/OCA) / `l10n_bg_erp_net_fp_iot` (EE) — Odoo IoT-box bridges

## Known limitations

- Direct browser→device printing needs the ErpNet.FP service reachable
  from each cashier machine.
- PLU device capacity is finite (~10000); large catalogues need
  curation of which products are PLU-pushed.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- PLU concept: `claude.ai/memory/reference_fiscal_plu_concept.md`
- `readme/` — DESCRIPTION source notes
