# ErpNet.FP ↔ OCA iot_oca Bridge (Community)

> CE-friendly bridge between `l10n_bg_erp_net_fp` and OCA's `iot_oca`
> module — exposes ErpNet.FP scales/devices as iot_oca systems and
> backs the packaging-weight QC. Auto-installs when both are present.

**Module:** `l10n_bg_erp_net_fp_iot_oca` | **Version:** 18.0.11.0.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

Odoo Enterprise has a native `iot.box`; the Community/OCA world uses
OCA's `iot_oca`. This bridge lets the ErpNet.FP fiscal/peripheral
layer integrate with `iot_oca` on Community installs (the Enterprise
counterpart is `l10n_bg_erp_net_fp_iot`). It auto-installs only when
both `l10n_bg_erp_net_fp` and `iot_oca` are present.

## What it provides

- `action_create_matching_iot_oca_system` — registers an ErpNet.FP
  device as an `iot_oca` system so it appears in the OCA IoT UI.
- `erp_net_fp_kind` Selection on the iot system — lets the
  packaging-weight QC mixin filter for scales specifically.
- `read_weight()` — synchronous HTTP GET to the parent ErpNet.FP
  system; the public API the Phase 3 packaging-weight QC mixin
  (`l10n.bg.packaging.weighable.mixin`) calls to verify MO/picking
  weight against the BoM expected ± tolerance.
- `action_verify_packaging_weight` — runs the QC check.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `iot_oca`, `mrp`, `stock` | `l10n_bg_erp_net_fp` |

## Configuration

Auto-installs when `l10n_bg_erp_net_fp` + `iot_oca` are both
installed. Then register ErpNet.FP scales as iot_oca systems and use
the packaging-weight QC on MOs / pickings.

## Sibling

`l10n_bg_erp_net_fp_iot` (in l10n-bulgaria-ee) is the Enterprise
`iot.box` equivalent of this Community bridge.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Device layer: `l10n_bg_erp_net_fp`
- Enterprise equivalent: `l10n-bulgaria-ee/l10n_bg_erp_net_fp_iot`
