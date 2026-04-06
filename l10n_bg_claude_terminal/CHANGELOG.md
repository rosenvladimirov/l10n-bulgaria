# Changelog

## 18.0.1.6.0

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

## 18.0.1.3.0

- Add AI button in list view (next to New, same CSS)
- Add modal dialog with Claude Terminal panel for list views
- Export ClaudeTerminalPanel for reuse across components

## 18.0.1.2.0

- Initial chatter integration with toggle button and terminal panel
- Per-user configuration (terminal URL, Odoo RPC, Telegram, Viber MCP)
- Dark theme (Catppuccin Mocha) with expand/collapse support
