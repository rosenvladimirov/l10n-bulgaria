# Changelog

## 19.0.1.15.0

### Added — AI Tokenizer foundation (Qdrant + Ollama) — ported from 18.0.1.20.x
- Six new models for vector tokenization of Odoo records:
  - `ai.view.registry` — per-model+view entries with `Re-parse Arch` / `Tokenize All` / `Documents` actions.
  - `ai.composite.document` — generated documents (token count + embedding reference).
  - `ai.view.parser` — extracts tokenizable fields from view arch, filtering system/chatter fields via `EXCLUDED_FIELDS`.
  - `ai.embedding.provider` (AbstractModel) — dispatcher for Ollama / OpenAI / Voyage / Anthropic.
  - `ai.qdrant.client` (AbstractModel) — minimal Qdrant REST client.
  - `ai.document.builder` (AbstractModel) — flattens a record into structured text (`MAX_O2M_ROWS=100`, `MAX_M2M_NAMES=20`).
- New user fields (Claude Terminal tab): `claude_qdrant_url/api_key/collection_prefix`, `claude_ollama_url/model`, `claude_embedding_provider` (ollama/openai/voyage/anthropic), `claude_embedding_api_key`.
- `get_config()` payload now includes `ai_tokenizer` block exposing Qdrant/Ollama/provider configuration to MCP server.
- `action_test_connections` extended with Qdrant (`GET /collections`) and Ollama (`GET /api/tags` + model-pulled check) stages. Non-ollama providers skip Ollama check cleanly.
- New menu `Administration → AI Tokenizer` (View Registry, Composite Documents) — restricted to `base.group_system`. ACLs: user read / system full access on both models.
- Frontend OWL status widget (`ai_tokenizer_status.js/xml/scss`) registered in `web.assets_backend`.
- CodeEditor `mode` option on `field_spec` uses `javascript` (Odoo validates against `["javascript","xml","qweb","scss","python"]` — `json` would throw `OwlError: 'mode' is not valid`).

## 19.0.1.14.0

### Added — Anthropic API Key pre-authentication
- New `claude_anthropic_api_key` field on res.users (Settings → Preferences → Claude Terminal)
- When set, passes `ANTHROPIC_API_KEY` as environment variable to the terminal session
- Claude Code CLI starts pre-authenticated — no login prompt on every terminal open
- User can still re-authenticate manually with `/login` inside the terminal
- Supported in all terminal modes: chatter, list view dialog, kanban view dialog
- Works in both local and external terminal modes

## 19.0.1.13.1

### Fix Test Connections — switch from bus to display_notification chain
- Root cause: returning `False` from a button triggers `ir.actions.act_window_close`
  in `action_service.js` (line 1242: falsy → `{type: "ir.actions.act_window_close"}`)
  which closes the preferences dialog
- Fix: return a `display_notification` action chain; chain terminates when the last
  item has no `next` → `client_actions.js` returns `undefined` → `if (next)` is false
  → dialog stays open
- Remove `bus.bus._sendone` loop and `notifs` list; no bus channel needed for this

## 19.0.1.13.0

### Port claude_theme, Web Session and MCP Server from v18
- New field `claude_theme` (Selection) — terminal color theme, default `github`
- New fields `claude_web_url`, `claude_web_db`, `claude_web_login`,
  `claude_web_password` — Web Session connector configuration
- New fields `claude_mcp_url`, `claude_mcp_token`, `claude_mcp_client_id`,
  `claude_mcp_api_key` — MCP Server configuration
- `_CLAUDE_FIELDS` updated to include all new fields (SELF_READABLE/WRITEABLE)
- `get_claude_mcp_config()` now returns `theme`, `web_session`, `mcp_server`
- View: added `claude_theme` to "Claude Terminal" group; added "Web Session"
  and "MCP Server" groups between "Odoo RPC Connector" and the button row

## 19.0.1.12.3

### Inline type mapping in action_test_connections
- Remove local `def notif_type(status)` helper — inline the dict lookup
  directly in the `_sendone` payload: `{"ok": "success", ...}.get(n["status"], "info")`

## 19.0.1.12.2

### Use bus simple_notification for connection test toasts
- `action_test_connections` uses `bus.bus._sendone(..., "simple_notification", ...)`
  — the standard Odoo built-in handler in `bus/simple_notification_service.js`
- No custom JS needed; 3 separate sticky toasts, form stays open

## 19.0.1.12.1

### Fix Sticky Notifications — Revert to display_notification
- Replace bus approach with direct `display_notification` chain
- `next` is inside `params` (confirmed from Odoo JS source: `client_actions.js`)
- `False` as terminal stops the chain cleanly

## 19.0.1.12.0

### Refactor Connection Tests — Bus Notifications
- Remove `claude.terminal.test.wizard` transient model (no longer needed)
- `action_test_connections` now sends each result as a separate bus
  notification via `claude_terminal/notification` channel and returns `False`
- `terminal_refresh_service.js` subscribes to `claude_terminal/notification`
  and shows sticky toasts via the Odoo notification service — form stays open

## 19.0.1.11.1

### Fix Sticky Notifications Chain
- Move `next` to root level of the action dict (Odoo 17+ style) + keep in
  `params` for backward compat — fixes chained toasts not appearing
- Use `False` as terminal instead of `{"type": "ir.actions.do_nothing"}`

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
