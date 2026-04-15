# Changelog

## 18.0.1.21.2

### Security — Restrict access to Claude MCP secrets
- `get_claude_mcp_config()` now requires `base.group_system`. Previously any logged-in user (including portal/internal with minimal rights) could RPC-call this method and receive plaintext: Anthropic API key, MCP token, Telegram api_hash, Viber bot token, web-session password, **company-level Qdrant + embedding API keys**.
- `res.company.claude_qdrant_api_key` and `res.company.claude_embedding_api_key` now declare `groups="base.group_system"` — read access enforced at ORM level, not just UI password masking. Same on the related fields in `res.config.settings`.

## 18.0.1.21.1

### Fixed — Manifest `website` URL
- Was pointing to `nicePrintBulgaria/l10n-bulgaria` (wrong account). Now points to the actual repo and module subpath: `rosenvladimirov/l10n-bulgaria/tree/18.0/l10n_bg_claude_terminal`.

## 18.0.1.21.0

### Changed — AI Tokenizer config moved from `res.users` to `res.company`
- **Rationale**: Qdrant endpoint, Ollama endpoint, embedding provider and API keys are infrastructure settings that belong to the company, not to each user. Per-user storage caused duplicate config and meant each user had to set them independently.
- New model: `res.company` with seven fields (`claude_qdrant_url`, `claude_qdrant_api_key`, `claude_qdrant_collection_prefix`, `claude_ollama_url`, `claude_ollama_model`, `claude_embedding_provider`, `claude_embedding_api_key`).
- New model: `res.config.settings` exposes those as related fields; new UI block "AI Tokenizer (Qdrant + Ollama)" in Settings → General Settings (inherits `base_setup.res_config_settings_view_form`).
- Removed the same seven fields from `res.users` and from the "AI Tokenizer" group in My Profile → Claude Terminal tab.
- `action_test_connections` and `get_config()` now read from `user.company_id.claude_*`.
- Added dependency `base_setup` (for the General Settings form inheritance anchor).

### Migration — `migrations/18.0.1.21.0/post-migration.py`
- Copies existing `res_users.claude_qdrant_*/ollama_*/embedding_*` values from the first admin user (`base.group_system`) into `res_company` row id=1, but only for fields that are still empty on the company — prevents overwriting values already set directly on the company.
- Drops the legacy user columns afterwards (Odoo doesn't auto-drop removed fields).
- Idempotent: if columns are already gone or no legacy values exist, migration is a no-op.

## 18.0.1.20.1

### Fixed — CodeEditor `mode` prop validation error on AI View Registry form
- `field_spec` used `widget="ace" options="{'mode': 'json'}"` but Odoo 18 CodeEditor only accepts `javascript|xml|qweb|scss|python` (validated via `CodeEditor.MODES`).
- Changed to `'mode': 'javascript'` — JSON content is still highlighted correctly (JSON is a valid JavaScript subset).
- Symptom: `OwlError: Invalid props for component 'CodeEditor': 'mode' is not valid` when opening the AI View Registry form view.

## 18.0.1.20.0

### Added — Qdrant + Ollama checks in Test Connection chain
- `action_test_connections` extended with two new stages: Qdrant (`GET /collections`) and Ollama (`GET /api/tags` — verifies the configured embedding model is actually pulled).
- When `claude_embedding_provider != 'ollama'`, the Ollama stage reports `warn` with the active provider name (no spurious errors for OpenAI/Voyage/Anthropic setups).
- Qdrant stage distinguishes missing api-key (HTTP 401/403 → `warn`) from real connectivity errors.

### Added — `ai_tokenizer` block in `get_config()` payload
- MCP server now receives Qdrant/Ollama/provider configuration from the Odoo user profile, no separate MCP-side config needed.
- Fields exposed: `enabled`, `qdrant_url`, `qdrant_api_key`, `collection_prefix`, `ollama_url`, `ollama_model`, `provider`, `embedding_api_key`.

### Added — Frontend AI Tokenizer status widget
- New OWL component (`ai_tokenizer_status.js/xml/scss`) registered in `web.assets_backend` — shows per-collection parse/tokenize progress.

## 18.0.1.19.0

### Added — AI Tokenizer foundation (Qdrant + Ollama)
- Six new models wire up vector tokenization of Odoo records:
  - `ai.view.registry` — per-model+view entries with `Re-parse Arch` / `Tokenize All` / `Documents` actions.
  - `ai.composite.document` — generated documents (token count + embedding vector reference).
  - `ai.view.parser` — extracts tokenizable fields from view arch, filtering system/chatter fields via `EXCLUDED_FIELDS`.
  - `ai.embedding.provider` (AbstractModel) — dispatcher for Ollama / OpenAI / Voyage / Anthropic.
  - `ai.qdrant.client` (AbstractModel) — minimal REST client covering collection and point lifecycle.
  - `ai.document.builder` (AbstractModel) — flattens a record into structured text (`MAX_O2M_ROWS=100`, `MAX_M2M_NAMES=20`).
- New user fields (Claude Terminal tab): `claude_qdrant_url/api_key/collection_prefix`, `claude_ollama_url/model`, `claude_embedding_provider` (ollama/openai/voyage/anthropic), `claude_embedding_api_key`.
- New menu `Administration → AI Tokenizer` with *View Registry* and *Composite Documents* entries (restricted to `base.group_system`).
- ACL entries for user read / system full access on both registry and document models.

## 18.0.1.18.0

### Fixed — Test Connection now honors `claude_odoo_protocol` selector
- Previously `action_test_connections` always used XML-RPC regardless of the protocol field — JSON-RPC selection was ignored.
- Now branches on `claude_odoo_protocol`: tries the chosen protocol first, then the other, then `/web/session/authenticate` as fallback.
- The notification message includes the protocol that actually succeeded: e.g. `[XML-RPC] Connected — UID 2, Odoo 18.0`.
- Web Session fallback works through reverse proxies (Cloudflare Access, Traefik, Nginx) that block `/xmlrpc/*` and `/jsonrpc` but allow `/web/*`.
- On total failure, message lists each attempt's error so misconfigurations are easier to diagnose.

## 18.0.1.17.0

### Changed — Claude Terminal page in "My Profile" (hr.res_users_view_form_profile)
- Reverted previous attempt to inherit `base.view_users_form` (admin-only Settings → Users)
- Now inherits `hr.res_users_view_form_profile` — the "My Profile" form opened from the avatar dropdown when `hr` is installed
- Each user sees only their own Claude Terminal config (not other users')
- Added `hr` to manifest depends

## 18.0.1.16.0

### Added — Claude Terminal page in main user form (REVERTED in 17.0)

## 18.0.1.15.0

### Added — OAuth token support + helper buttons (port from 19.0)
- `claude_anthropic_api_key` accepts both API keys (`sk-ant-api03-…`) and OAuth tokens (`sk-ant-oat01-…` from Pro/Teams/Max via `claude /login`)
- New action `action_open_anthropic_console` — opens Anthropic Console API Keys page
- New action `action_open_claude_oauth` — opens Claude.ai login page
- View redesigned with info panel + two helper buttons next to the field
- Updated help text to describe both auth modes

## 18.0.1.14.0

### Added — Anthropic API Key pre-authentication
- New `claude_anthropic_api_key` field on res.users (Settings → Preferences → Claude Terminal)
- When set, passes `ANTHROPIC_API_KEY` as environment variable to the terminal session
- Claude Code CLI starts pre-authenticated — no login prompt on every terminal open
- User can still re-authenticate manually with `/login` inside the terminal
- Supported in all terminal modes: chatter, list view dialog, kanban view dialog
- Works in both local and external terminal modes

## 18.0.1.13.0

### Fix Test Connections — switch from bus to display_notification chain
- Root cause: returning `False` from a button triggers `ir.actions.act_window_close`
  in `action_service.js` (line 1242: falsy → `{type: "ir.actions.act_window_close"}`)
  which closes the preferences dialog
- Fix: return a `display_notification` action chain; chain terminates when the last
  item has no `next` → `client_actions.js` returns `undefined` → `if (next)` is false
  → dialog stays open
- Remove `bus.bus._sendone` loop and `notifs` list; no bus channel needed for this

## 18.0.1.12.3

### Inline type mapping in action_test_connections
- Remove local `def notif_type(status)` helper — inline the dict lookup
  directly in the `_sendone` payload: `{"ok": "success", ...}.get(n["status"], "info")`

## 18.0.1.12.2

### Use bus simple_notification for connection test toasts
- `action_test_connections` uses `bus.bus._sendone(..., "simple_notification", ...)`
  — the standard Odoo built-in handler in `bus/simple_notification_service.js`
- No custom JS needed; 3 separate sticky toasts, form stays open

## 18.0.1.12.1

### Fix Sticky Notifications — Revert to display_notification
- Replace bus approach with direct `display_notification` chain
- `next` is inside `params` (confirmed from Odoo JS source: `client_actions.js`
  reads `params.next` and returns it for dispatch)
- `False` as terminal — JS treats it as falsy, stops the chain cleanly
- Remove `claude_terminal/notification` bus subscription from refresh service

## 18.0.1.12.0

### Refactor Connection Tests — Bus Notifications
- Remove `claude.terminal.test.wizard` transient model (no longer needed)
- `action_test_connections` now sends each result as a separate bus
  notification via `claude_terminal/notification` channel and returns `False`
- `terminal_refresh_service.js` subscribes to `claude_terminal/notification`
  and shows sticky toasts via the Odoo notification service — form stays open

## 18.0.1.11.1

### Fix Sticky Notifications Chain
- Move `next` to root level of the action dict (Odoo 17+ style) + keep in
  `params` for backward compat — fixes chained toasts not appearing
- Use `False` as terminal instead of `{"type": "ir.actions.do_nothing"}`

## 18.0.1.11.0

### Test Connections — Sticky Notifications
- Replaced modal wizard with 3 chained sticky toast notifications (one per
  connection type: Odoo RPC, MCP Server, Web Session)
- Preferences form stays open during/after testing
- `action_test_connections` now runs tests inline (no wizard dialog)
- Import `urllib.error` and `xmlrpc.client` added to `res_users.py`

## 18.0.1.10.0

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

## 18.0.1.9.0

### Odoo RPC API Key
- New field `claude_odoo_api_key` (Char, password) in the "Odoo RPC Connector"
  group — stores the Odoo API key used by the MCP server to authenticate against
  the configured Odoo instance
- `get_claude_mcp_config()` now returns `odoo.api_key`

## 18.0.1.8.0

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

## 18.0.1.7.0

- Add AI button in kanban view (next to New, reuses list view dialog)
- `KanbanController` patch: bus refresh listener for CLAUDE_REFRESH events

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
