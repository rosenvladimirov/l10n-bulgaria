# Changelog

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
