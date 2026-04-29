# Changelog

All notable changes to the l10n_bg_erp_net_fp module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
