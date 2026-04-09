# Changelog

## 19.0.1.11.0

### Test Connections — Sticky Notifications
- Replaced modal wizard with 3 chained sticky toast notifications
- `action_test_connections` runs tests inline; preferences form stays open
- `urllib.error` and `xmlrpc.client` imports added to `res_users.py`

## 19.0.1.10.0

### Test Connections Wizard
- New `claude.terminal.test.wizard` TransientModel — tests all three connection
  types (Odoo RPC, MCP Server, Web Session) and shows color-coded badge results:
  green (OK), yellow (Warning), red (Error)
- New button **Test Connections** in user preferences (opens the wizard dialog)

### Save to MCP Button
- New button **Save to MCP** in user preferences — POSTs the current Odoo
  instance connection config (`url`, `db`, `user`, `api_key`, `protocol`) to
  `{mcp_url}/api/user/connections` with `X-Api-Token` authentication
- Displays a success or error notification after the operation

## 19.0.1.9.0

### Odoo RPC API Key
- New field `claude_odoo_api_key` (Char, password) in the "Odoo RPC Connector"
  group — stores the Odoo API key used by the MCP server to authenticate against
  the configured Odoo instance
- `get_claude_mcp_config()` now returns `odoo.api_key`

## 19.0.1.8.0

### External Terminal Support
- New field `claude_use_external_terminal` (Boolean) — switch between local and
  external Docker terminal
- New field `claude_api_key` (Char) — Odoo API key for external auth
  (visible only when external mode is enabled)
- Both modes always use iframe (embedded in chatter/list/kanban):
  - **OFF**: iframe → local host ttyd (ODOO_ORIGIN params, no API key)
  - **ON**: iframe → external Docker terminal (API_KEY + ODOO_URL params)
- `get_claude_mcp_config()` now returns `use_external` and `api_key`

### Shared URL Builder
- New `terminal_utils.js` with `buildExternalTerminalUrl()` helper
- All external URL construction goes through one function

### Redesigned Terminal Panel UI
- New header: logo icon + "Claude" title + "Terminal" badge + model breadcrumb
- Status dot with glow effect (green=connected, yellow=loading, red=error)
- Status bar at bottom showing connection state + active model
- Refined SCSS: softer shadows, 10px radius, accent hover states
- Monospace breadcrumb for `model / #resId` context

### Theme
- Switched from dark Catppuccin Mocha to clean light theme matching Odoo UI
- White background, Odoo purple accent (#714ba0), light borders

## 19.0.1.7.0

- Add AI button in kanban view (next to New, reuses list view dialog)
- `KanbanController` patch: bus refresh listener for CLAUDE_REFRESH events

## 19.0.1.6.0

- Live refresh: MCP `odoo_write` / `odoo_create` now sends bus events with
  model, res_ids and changed field values.
- New bus channels: `claude_terminal/refresh_field`, `claude_terminal/refresh_list`.
- New `res.users` methods: `notify_claude_refresh_field`, `notify_claude_refresh_list`.
- `FormController` patch: flashes changed fields (blue glow) when Claude writes
  to the currently open record.
- `ListController` patch: highlights new rows (green flash) when Claude creates
  records in the currently open list.
- Companion MCP server changes: SQLite `SessionManager`, session registration
  endpoint, automatic notify hooks in `odoo_write`/`odoo_create`.

## 19.0.1.3.0

- Add AI button in list view (next to New, same CSS)
- Add modal dialog with Claude Terminal panel for list views
- Export ClaudeTerminalPanel for reuse across components

## 19.0.1.2.0

- Initial chatter integration with toggle button and terminal panel
- Per-user configuration (terminal URL, Odoo RPC, Telegram, Viber MCP)
- Dark theme (Catppuccin Mocha) with expand/collapse support
