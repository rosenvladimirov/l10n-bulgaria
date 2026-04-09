# Changelog

## 16.0.1.12.2

### Use bus simple_notification for connection test toasts
- `action_test_connections` uses `bus.bus._sendone(..., "simple_notification", ...)`
  — the standard Odoo built-in handler in `bus/simple_notification_service.js`
- No custom JS needed; 3 separate sticky toasts, form stays open

## 16.0.1.12.1

### Fix Sticky Notifications — Revert to display_notification
- Replace bus approach with direct `display_notification` chain
- `next` is inside `params` (confirmed from Odoo JS source: `client_actions.js`)
- `False` as terminal stops the chain cleanly

## 16.0.1.12.0

### Refactor Connection Tests — Bus Notifications
- Remove `claude.terminal.test.wizard` transient model (no longer needed)
- `action_test_connections` now sends each result as a separate bus
  notification via `claude_terminal/notification` channel and returns `False`
- `terminal_refresh_service.js` handles `claude_terminal/notification` via
  addEventListener and shows sticky toasts — form stays open

## 16.0.1.11.1

### Fix Sticky Notifications Chain
- Move `next` to root level of the action dict (Odoo 17+ style) + keep in
  `params` for backward compat — fixes chained toasts not appearing
- Use `False` as terminal instead of `{"type": "ir.actions.do_nothing"}`

## 16.0.1.11.0

### Test Connections — Sticky Notifications
- Replaced modal wizard with 3 chained sticky toast notifications
- `action_test_connections` runs tests inline; preferences form stays open
- `urllib.error` and `xmlrpc.client` imports added to `res_users.py`

## 16.0.1.10.0

### Initial port from v18/v19
- Full port of `l10n_bg_claude_terminal` to Odoo 16.0
- Claude Terminal iframe panel in chatter (via ChatterTopbar patch — v16 uses
  LegacyComponent for Chatter, so we patch ChatterTopbar instead)
- AI button in list view and kanban view (modal dialog with terminal iframe)
- Live refresh: bus events `claude_terminal/refresh`, `claude_terminal/refresh_field`,
  `claude_terminal/refresh_list` forward to `env.bus` via `claude_refresh` service
- v16 compatibility notes:
  - `patch()` uses 3-argument form: `patch(obj, "name", { ... })`
  - Bus service uses `addEventListener('notification', ...)` (no `subscribe()`)
  - RPC uses `useService("rpc")` (no module-level `rpc` import)
  - ChatterTopbar is patched instead of Chatter; model/resId accessed via
    `this.props.record.chatter.thread`; reload via `reloadParentView()`

### Test Connections Wizard
- `claude.terminal.test.wizard` TransientModel — tests Odoo RPC, MCP Server,
  Web Session connections with color-coded badge results

### Save to MCP Button
- **Save to MCP** button in user preferences — POSTs connection config to MCP server

### Per-user configuration fields
- Claude Terminal URL, External Terminal toggle, API Key
- Odoo RPC Connector: URL, Database, Protocol, API Key
- Telegram MCP: API ID, API Hash, Phone, Session Name
- Viber MCP: Bot Token, Bot Name, Webhook URL
