# Changelog

## [19.0.15.3.0] - 2026-05-24

### Added — Community alternative to Enterprise `iot` + `pos_iot` for barcode readers

Replaces the licensed-only path for getting hardware barcode-reader scans into
Odoo. Subscribes the browser to the local Odoo.ErpNet.FP proxy's
`/readers/<id>/ws` WebSocket and forwards each scan to the existing Odoo
barcode-handling layer — same UX as if the reader were a keyboard wedge or an
EE IoT box.

- `static/src/services/erpnet_reader_service.js` — shared core service:
  auto-discovers active readers via `GET /readers`, subscribes to each via
  WebSocket with exponential-backoff reconnect, fans out scans through an
  Owl EventBus. Loaded into BOTH `web.assets_backend` and
  `point_of_sale._assets_pos`.
- `static/src/js/pos_barcode_bridge.js` — POS-side glue: pipes scans into
  the core POS `barcode_reader` service so existing screen handlers
  (product lookup, customer search, weight code, etc.) Just Work.
- `static/src/js/backend_barcode_bridge.js` — backend-side glue: triggers
  `barcode_scanned` on the core `barcode` service so existing form-view
  handlers (stock pickings, inventory, hr.attendance, …) Just Work.

Host resolution — single source of truth is `fiscal.printer.device.host`:
- POS context: `pos.config.l10n_bg_erp_net_fp_host` (already computed
  from `pos.config.l10n_bg_fiscal_printer_id.host`).
- Backend context: `searchRead` the first active proxy-mode device.

No `ir.config_parameter` to set, no extra config screen. If no device
is configured the reader bridge stays silent (consumers can still
call `.subscribe()` — they just get nothing).

Pure browser ↔ WebSocket — no server-side bus.bus, no Odoo controller,
no extra cron. Hot-plug: service re-scans `/readers` every 30 s.

*Assisted by Claude Code*

## [19.0.15.2.0] - 2026-05-22

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

All notable changes to the l10n_bg_erp_net_fp module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [19.0.10.0.0] - 2026-05-06

### Added — Packaging weight QC (Phase 3, mirrors 18.0.10.0.0)

See 18.0.10.0.0 for the full feature list. Added: `mrp` and `stock` dependencies, `l10n.bg.packaging.weighable.mixin`, MO + picking + BoM extensions, company-level defaults, "Verify package weight" buttons + Packaging QC notebook pages.

*Assisted by Claude Code*

## [19.0.9.0.0] - 2026-05-06

### Added — Native Odoo IoT Box integration (mirrors 18.0.9.0.0)

- New hard dependency: `iot` (EE module). Clients on Community Edition without the EE `iot` module must stay on the 19.0.8.4.x branch.
- `iot.box.connection_mode` field (`direct` / `proxy`) with auto-detection from host
- `iot.box.erp_net_fp_url` + `iot.box.erp_net_fp_ssl_verify` fields
- `iot.box._rpc_proxy_to_iot()` — browser-via-server fallback
- `iot.device.action_via_proxy(payload, timeout)` — universal server-side dispatch
- `iot.device.read_weight()` — convenience wrapper for scale devices
- New table `iot.device.response` — generic response store, separate from `fiscal.printer.response`
- "Discover ErpNet.FP devices" wizard — auto-creates `iot.device` records from `/scales`, `/displays`, `/readers`, `/printers`, `/pinpads`
- Bridge `fiscal.printer.device` → `iot.box` — "Create matching IoT Box" button + bidirectional URL sync via `write()` override
- JS: `IoTLongpolling._rpcIoT` patched. **v19 imports from `@iot/network_utils/iot_longpolling`** (different from v18 `@iot/iot_longpolling`).
- JS: bus subscriber on channel `iot.device.request`

### Backward compatibility

- `fiscal.printer.device` flow unchanged
- New IoT integration is opt-in
- All new code is ADD-only

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
