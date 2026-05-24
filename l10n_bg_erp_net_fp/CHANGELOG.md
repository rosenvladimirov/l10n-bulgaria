# Changelog

All notable changes to the l10n_bg_erp_net_fp module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.15.2.0] - 2026-05-22

### Added — `fiscal_plu_eligible` opt-out flag

- `product.template.l10n_bg_fiscal_plu_eligible` (Boolean, indexed, default
  True) — marks whether a product should occupy a PLU slot on the fiscal
  device.
- `product.product.l10n_bg_fiscal_plu_eligible` — related store=True for fast
  filtering and inclusion in `_load_pos_data_fields()`.
- When False, sales fall back to free-price entry (Datecs cmd 0x31): name and
  price travel per-receipt instead of being programmed once. Designed for
  long-tail items so the limited PLU table (3000 slots on FP-class devices
  like BlueCash-50) stays for hot SKUs.
- Default True (opt-out) — preserves current behaviour for existing
  databases.
- Native BlueCash client (`BlueCash.PluClient`, repo
  `~/Проекти/odoo/iot/BlueCash.PluClient`) reads this field to build the
  push set.

### Resolves

Open question #4 from the BlueCash PLU Client architecture doc
(`~/Свалени/CLAUDE(1).md` §10).

*Assisted by Claude Code*

## [18.0.10.0.0] - 2026-05-06

### Added — Packaging weight QC (Phase 3)

- New abstract mixin `l10n.bg.packaging.weighable.mixin` — encapsulates the read-scale → compare-vs-expected ± tolerance → write-state → notify flow. Reused by `mrp.production` and `stock.picking`.
- `mrp.production.action_verify_packaging_weight()` — reads the configured scale via `iot.device.read_weight()` (Phase 2), computes expected weight from BoM lines × MO scaling factor, compares ± tolerance, writes `packaging_weight_state` (pending / pass / fail) plus actual / expected / verified-at / message fields.
- `stock.picking.action_verify_packaging_weight()` — same pattern, expected weight summed over move lines.
- `mrp.bom.weight_tolerance_percent` — per-BoM tolerance % override
- `mrp.bom.package_empty_weight` — weight of the empty box / crate (kg) added to expected total
- `res.company.default_packaging_tolerance_percent` (default 5 %)
- `res.company.default_packaging_scale_id` — fall-through scale device when MO/picking doesn't override
- `res.company.default_packaging_empty_weight` — fall-through empty weight for pickings
- New header buttons "Verify package weight" on MO and picking forms
- New "Packaging QC" notebook page on MO + picking forms (state badge + actual + expected + verified-at + message)
- New "Packaging Weight QC" app block in Settings (company defaults)

### Dependencies

- Added `mrp` and `stock` to `depends`. Both are CE-available, so this is not a license-edition jump (unlike the 18.0.9.0.0 `iot` dep).

### Backward compatibility

- All new fields are optional and default to safe no-ops. Existing MOs / pickings / BoMs continue working without verification — the workflow is opt-in via the explicit "Verify package weight" button.
- No existing field, method, or view ID was changed.

*Assisted by Claude Code*

## [18.0.9.0.0] - 2026-05-06

### Added — Native Odoo IoT Box integration (Phase 2.a + 2.b + 2.c)

- New hard dependency: `iot` (EE module). Clients on Community Edition without the EE `iot` module must stay on the 18.0.8.4.x branch.
- `iot.box.connection_mode` field (`direct` / `proxy`) with auto-detection from host (`192.168.*`, `10.*`, `.local` → `proxy`)
- `iot.box.erp_net_fp_url` + `iot.box.erp_net_fp_ssl_verify` fields — link an `iot.box` record to an ErpNet.FP instance
- `iot.box._rpc_proxy_to_iot()` server method — browser-via-server fallback when the browser cannot reach the IoT Box directly
- `iot.device.action_via_proxy(payload, timeout)` — universal server-side dispatch helper. Routes through `direct` HTTP or `proxy` (bus.bus → browser → IoT Box → response) based on the parent `iot.box.connection_mode`
- `iot.device.read_weight()` — convenience wrapper for scale-type devices (used by future MO / picking weight verification flows)
- New table `iot.device.response` — generic response store for browser-proxied IoT actions; mirrors `fiscal.printer.response` lifecycle but stays separate so legacy fiscal flow is untouched
- JS: `IoTLongpolling._rpcIoT` patched — when `iot.box.connection_mode == 'proxy'`, browser tunnels its IoT requests through Odoo `iot.box._rpc_proxy_to_iot` instead of fetching `iot_ip` directly
- JS: bus subscriber on channel `iot.device.request` — receives server-initiated IoT actions, fetches the IoT Box URL on the server's behalf, writes result into `iot.device.response`
- View: `iot.box` form extended with "ErpNet.FP Integration" section (URL, SSL verify, connection mode) and "Discover ErpNet.FP devices" header button
- Wizard `iot.discover.wizard` — opens from `iot.box` form, queries `GET /scales`, `/displays`, `/readers`, `/printers`, `/pinpads` of the linked ErpNet.FP, presents the discovered devices in a checkbox list, creates `iot.device` records (with proper `<kind>.<id>` identifier) on confirm. Idempotent — re-running skips already-configured devices.
- Bridge `fiscal.printer.device` → `iot.box` — new `iot_box_id` Many2one + "Create matching IoT Box" button on the printer form. `fiscal.printer.device` stays the source of truth for `host` / `printer_id` / `connection_mode` / `ssl_verify`; iot.box mirrors them on every `write()`.

### Backward compatibility

- `fiscal.printer.device` flow is **unchanged** — same model, same fields, same RPC paths, same `fiscal.printer.response` table. Existing clients can upgrade without changing their fiscal printer setup.
- New IoT integration is **opt-in** — activated only when an `iot.box` record is created with an ErpNet.FP URL. Otherwise the module behaves exactly as 18.0.8.4.x.
- All new code is ADD-only; no existing model fields, methods, view IDs, or JS service names were renamed or removed.

### Why

- Native `pos_iot.scale_screen` button "Тегли" → reads weight via `iot.device` → now works against ErpNet.FP scales without a custom widget
- Native scanner long-poll → barcode events from ErpNet.FP `reader.<id>` flow into POS, quality, picking, and any other native iot.device consumer
- Native `pos_iot` customer-display update → maps to ErpNet.FP `display.<id>`
- Foundation for future MO / picking weight-verification flows (Phase 3) and any custom form `<button>` that needs scale input

*Assisted by Claude Code*

## [18.0.7.1.3] - 2026-03-21

### Added
- Heartbeat now writes to `fiscal.printer.status` history on status change (online/unreachable transitions only, not every 30s)
- `browser_ready` creates initial `browser_connected` status record when browser connects

### Fixed
- Health check `checkPrinterReachable` now falls back to `no-cors` fetch when CORS fails — opaque response is enough to confirm host is up
- Added SSL hint in unreachable notification: if host uses HTTPS, user is prompted to open the printer URL in a new tab first to accept the self-signed certificate

*Assisted by Claude Code*

## [18.0.7.1.0] - 2026-03-21

### Added
- Browser proxy connection tracking: `proxy_last_seen`, `proxy_user_id`, `proxy_printer_ok`, `proxy_connected` fields on `fiscal.printer.device`
- Heartbeat mechanism: browser sends periodic health checks every 30s via `/fiscal_printer/heartbeat`
- `/fiscal_printer/browser_ready` now returns list of proxy printers for health check
- Pre-request validation in `_make_proxy_request` — immediately raises a clear error if no browser is connected or printer is unreachable (instead of waiting for timeout)
- Startup notification in browser: shows reachable/unreachable proxy printers on service init
- "Browser Proxy Status" section in device form view (visible only in proxy mode)
- `proxy_connected` and `proxy_printer_ok` columns in device list view with row decoration

### Changed
- All user-facing messages (errors, notifications) switched to English; code comments remain in Bulgarian
- Reduced verbose logging in `_make_proxy_request` — cleaner log output
- Improved error messages with full printer config details (name, host, printer ID, full URL, endpoint, connected user)
- Timeout error now includes endpoint and URL info for easier debugging

*Assisted by Claude Code*

## [18.0.7.0.2] - 2026-03-01

### Added
- Initial changelog entry
