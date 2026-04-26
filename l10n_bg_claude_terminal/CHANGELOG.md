# Changelog

## 19.0.1.29.0 — Setup wizard (5-step) for ZIP-based key configuration

New `claude.terminal.setup.wizard` (TransientModel) — standard Odoo 5-step
wizard for onboarding clients without manual ir.config_parameter editing.
Mirror of `l10n_bg_claude_terminal` 18.0.1.31.0 — code is identical.

### Flow
1. Качете конфигурация — upload password-protected ZIP (from MCP server's
   `mcp_terminal_get_config` tool).
2. Прегледайте ключовете — extracted JSON keys grouped by MCP / Anthropic
   / Qdrant / Embeddings, editable inline.
3. Изберете потребители — pick company + per-user list for Anthropic key.
4. Прилагане — writes company-level fields to `res.company`, Anthropic key
   per-user to `res.users.claude_api_key`, marks `claude_keys_rotated_at`.
5. Тестване — pings MCP `/api/health`, Anthropic Messages API, Qdrant
   `/collections`. Per-channel OK/FAIL with log.

### External dependency
- `pyzipper>=0.3.6` for AES-encrypted ZIP read. The MCP server emits AES
  via the same library; stdlib zipfile cannot decrypt AES.

### Files
- `wizards/__init__.py`, `wizards/claude_terminal_setup_wizard.py`,
  `wizards/claude_terminal_setup_wizard_views.xml`
- `security/ir.model.access.csv`: + `access_claude_terminal_setup_wizard`
- Menu: `Settings → Technical → Настройка с ZIP конфигурация`

## 19.0.1.27.0 — API key rotation tracking (Gap 4.7)

### Added
- `res.company.claude_keys_rotated_at` (Datetime) — кога е
  извършвано последното ротиране на AI секретите.
- Computed `claude_keys_age_days` и `claude_keys_needs_rotation`
  (True когато age ≥ 90 дни). Всички `groups="base.group_system"`.
- `action_mark_keys_rotated()` на `res.company` — маркира
  сегашния момент като "keys rotated now". Викан през бутон в
  Settings → General → AI Tokenizer → API Key Rotation.
- UI блок в General Settings: текуща възраст, warning banner при
  изтекъл срок, "I rotated the keys" бутон.
- Advisory-only: никой flow не се блокира; цел е admins да не
  забравят да ротират, не enforcement.

## 19.0.1.26.0 — Qdrant cross-company isolation guard (Gap 4.6)

### Changed
- `ai.qdrant.client.search()` автоматично добавя
  `must: [{key: "company_id", match: {value: <env.company.id>}}]` към
  filter-а, освен ако caller не подаде `filters={"_skip_company_guard":
  True, ...}`. Намалява риска за cross-company leak в multi-company
  instance, когато consumer забрави да филтрира ръчно.
- Collection name scoping (prefix × db_name) остава непокътнат —
  database-level isolation беше здрав, company-level беше best-effort.
- Transparent за single-company installs (auto-filter е no-op когато
  цялата колекция е от една компания).

## 19.0.1.25.0

### Removed — `claude_anthropic_api_key` field and per-user Anthropic pre-auth
- `res.users.claude_anthropic_api_key` field премахнат. Не се попълва вече
  от UI (Settings → Preferences → Claude Terminal) и не се връща от
  `get_claude_mcp_config`. Client-а (chatter/list/kanban) не подава
  `ANTHROPIC_API_KEY` към terminal URL.
- `action_open_anthropic_console` и `action_open_claude_oauth` премахнати —
  бяха button-и за водене до platform.claude.com и claude.ai/login, но
  вече няма поле, в което да се пасне резултата.
- `buildExternalTerminalUrl()` signature — седмият параметър
  `anthropicApiKey` премахнат. OWL props (`ClaudeTerminalPanel`,
  `ClaudeTerminalDialog`) също загубват `anthropicApiKey`.
- **Новата архитектура:** ако terminal container-а има `ANTHROPIC_API_KEY`
  env var (docker-compose / Portainer), `start-session.sh` export-ва го
  и Claude CLI го чете — т.е. **server-side fallback**. Ако няма —
  Claude CLI стартира без preset и потребителят прави `/login` в
  терминала (OAuth flow → `~/.claude/credentials.json`).
- Migration note: съществуващите стойности в `claude_anthropic_api_key`
  остават в базата до следващата миграция (полето е `fields.Char`,
  Odoo не drop-ва колоната автоматично). При нужда — `ALTER TABLE
  res_users DROP COLUMN claude_anthropic_api_key`.

## 19.0.1.23.0

### Fixed — AI Tokenizer: skip fields that raise AttributeError
- `ai.document.builder._render_spec_item` и `_render_one2many` сега
  улавят всяко изключение при четене на field (compute/related в
  3rd-party модул може да е счупен на Odoo 19). Вместо цял документ
  да влезе в state `error`, проблемното поле/клетка се пропуска и се
  логва warning. Документите се индексират с наличните полета.
- Конкретен trigger: `stock_move_forced_lot_multi_dimension` (OCA)
  на Odoo 19 още извиква `uom.uom.category_id`, което Odoo 19 премахна
  (`uom.uom` вече не е под `uom.category`, а е self-hierarchical през
  `relative_uom_id` + `parent_path`). Всички 16 документа в
  `purchase.order` на dev-19 бяха в error → сега ще се индексират.

## 19.0.1.22.0

### Changed — Unified MCP auth (task 6 от MCP unified auth plan)
- `terminal_utils.js` `buildExternalTerminalUrl()` docstring разширен:
  описва как предадените URL параметри (API_KEY, ODOO_URL, ODOO_DB,
  ODOO_USER) стават `Authorization: Bearer` + `X-Odoo-*` заглавки в
  `start-session.sh` на terminal контейнера. MCP middleware ги
  валидира през XMLRPC и resolve-ва profile — identify() не се вика
  експлицитно от JS вече.
- `res_users.claude_api_key` help text обновен да опише новата двойна
  роля: удостоверяване за външния terminal + MCP unified-auth. Cache
  TTL за key rotation е ~5 мин (AUTH_CACHE_TTL env).
- Няма code changes по rendering страна — всички нужни полета вече се
  предават от `get_claude_mcp_config` и `buildExternalTerminalUrl`.
- Port на 18.0.1.27.0.

## 19.0.1.21.0

### Added — Optional `Authorization: Bearer` header за Ollama embeddings
- `_embed_ollama` вече чете `company.claude_embedding_api_key` и ако има стойност
  го изпраща като `Authorization: Bearer <token>` header.
- Позволява ползване на proxied Ollama endpoint (напр. `https://mcp.odoo-shell.space/ollama`
  с MCP server passthrough, който валидира `OLLAMA_API_KEY`).
- Backward compatible: празен ключ → няма header (директен локален Ollama работи както преди).
- Help text на `claude_embedding_api_key` обновен — вече обхваща и proxied Ollama.

## 19.0.1.20.0

### Added — `_explanation` backport (20.0 forward-compat)
- Monkey patch в `__init__.py`: `models.Model._explanation = None` (guard-нат с
  `hasattr`, така че на 20.0 става no-op). Един ред → всички Odoo модели на
  16/17/18/19 получават Python class attribute като на 20.0.
- Нов модел `ir.model` extension → `get_ai_explanations(model_names=None, lang=None)`:
  MRO walk по `_reflect_model_params` pattern от Odoo 20 core, с
  lang-filtering parser за markers `[xx_YY]...[/xx_YY]`.
- Unmarked legacy текст се третира като `en_US` — видим само за english
  сесии, skip за останалите.
- Whitelist: само активни `ai.view.registry` модели се exposing-ват (consistency
  с tokenizer access rules; sensitive/transient/abstract модели отпадат
  автоматично).
- Tests в `tests/test_ai_explanations.py` — parser unit tests + registry
  whitelist integration tests.

### Why
Skills ecosystem (v3) ще декларира `_explanation` върху core модели (sale.order,
account.move, etc.) за да подава AI context към LLM без hardcoded dependency
на версия. Този base е 100% forward-compat с Odoo 20 native behavior.

## 19.0.1.19.0

### Same as 18.0.1.24.0 — port from v18
- AI Tokenizer секция върната в `base.view_users_form_simple_modif` (preferences modal).
- Седем related полета на `res.users` сочещи към `company_id.claude_*` — `readonly=False`, редакцията делегира към `res.company` (API ключовете остават `groups="base.group_system"`).
- Петте безопасни полета добавени в `SELF_WRITEABLE_FIELDS`.
- Данните остават company-level (архитектурата от 1.16.0 е запазена) — това е само UI surface.

## 19.0.1.18.0

### Same as 18.0.1.23.0 — port from v18
- Fix stale `user.claude_*` refs in `ai.qdrant.client` and `ai.embedding.provider` (broken since 1.16.0 res.company move).
- New: `ai.composite.document.search_similar()` semantic search API.
- New: `ai.composite.document.collection_stats()`.
- New: `ir.cron` "AI Tokenizer — re-index stale documents" (`cron_reindex_stale`, batch_size=50, disabled by default).

## 19.0.1.17.0

### Added — Form View Grabber on `ai.view.registry`
- Port from 18.0.1.22.0. Виж changelog на v18 за пълно описание: `action_scan_form_views()` сканира `ir.ui.view` form-ове, създава inactive registry entries за нови (model, form) комбинации; prefix + exact blacklist на технически модели; пропуска transient/abstract/неавтоматични модели.
- Header button "Scan Form Views" (`btn-primary`, с confirm) и server action в Actions gear menu.

### Fixed — `_is_enabled` reads from company, not user
- Stale след res.users → res.company move (v1.16.0).

## 19.0.1.16.1

### Security — Restrict access to Claude MCP secrets
- `get_claude_mcp_config()` now requires `base.group_system`. Previously any logged-in user (including portal/internal with minimal rights) could RPC-call this method and receive plaintext: Anthropic API key, MCP token, Telegram api_hash, Viber bot token, web-session password, **company-level Qdrant + embedding API keys**.
- `res.company.claude_qdrant_api_key` and `res.company.claude_embedding_api_key` now declare `groups="base.group_system"` — read access enforced at ORM level, not just UI password masking. Same on the related fields in `res.config.settings`.

## 19.0.1.16.0

### Changed — AI Tokenizer config moved from `res.users` to `res.company`
- Port from 18.0.1.21.0. Same structure: seven fields moved to `res.company`, `res.config.settings` exposes them as related fields with a new block "AI Tokenizer (Qdrant + Ollama)" in General Settings (inherits `base_setup.res_config_settings_view_form`).
- Removed the fields from `res.users` and the AI Tokenizer group in My Profile → Claude Terminal tab.
- `action_test_connections` and `get_config()` now read from `user.company_id.claude_*`.
- Added dependency `base_setup`.

### Fixed — Manifest `website` URL
- Was pointing to `nicePrintBulgaria/l10n-bulgaria`. Corrected to `rosenvladimirov/l10n-bulgaria/tree/19.0/l10n_bg_claude_terminal`.

### Migration — `migrations/19.0.1.16.0/post-migration.py`
- Copies legacy `res_users.claude_qdrant_*/ollama_*/embedding_*` values from the first admin user into `res_company` id=1 (only for empty company fields), then drops the legacy columns.
- Idempotent: no-op if legacy columns are absent or no values were set.

## 19.0.1.15.1

### Fixed — Search view compliance with Odoo 19 RelaxNG schema
- `<group expand="0" string="Group By">` wrapping group-by filters caused `RELAXNG_ERR_INVALIDATTR: Invalid attribute expand for element group` (v19 search `<group>` allows only `colspan/rowspan/fill/height/width/name/color/invisible`).
- Replaced with top-level `<separator/>` + `<filter context="{'group_by': ...}">` — v19 client auto-collects them into the Group By submenu.

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
