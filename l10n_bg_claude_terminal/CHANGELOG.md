# Changelog

## 16.0.1.13.1

### Fix Test Connections — switch from bus to display_notification chain
- Root cause: returning `False` from a button triggers `ir.actions.act_window_close`
  in `action_service.js` (line 1242: falsy → `{type: "ir.actions.act_window_close"}`)
  which closes the preferences dialog
- Fix: return a `display_notification` action chain; chain terminates when the last
  item has no `next` → `client_actions.js` returns `undefined` → `if (next)` is false
  → dialog stays open
- Remove `bus.bus._sendone` loop and `notifs` list; no bus channel needed for this

## 16.0.1.13.0

### Port Web Session and MCP Server view groups from v18
- View: added `claude_theme` to "Claude Terminal" group
- View: added "Web Session" group (`claude_web_url`, `claude_web_db`,
  `claude_web_login`, `claude_web_password`)
- View: added "MCP Server" group (`claude_mcp_url`, `claude_mcp_token`,
  `claude_mcp_client_id`, `claude_mcp_api_key`)
- Groups appear between "Odoo RPC Connector" and the action buttons
  (model fields were already present since 16.0.1.10.0)

## 16.0.1.12.3

### Inline type mapping in action_test_connections
- Remove local `def notif_type(status)` helper — inline the dict lookup
  directly in the `_sendone` payload: `{"ok": "success", ...}.get(n["status"], "info")`

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
