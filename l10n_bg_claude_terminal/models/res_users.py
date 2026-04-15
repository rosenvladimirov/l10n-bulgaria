# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import ssl
import urllib.request
import urllib.error
import xmlrpc.client

from odoo import _, api, fields, models
from odoo.service.db import list_dbs

import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    # ── Terminal ──
    claude_terminal_url = fields.Char(
        "Claude Terminal URL",
        help="URL of the terminal-control-mcp web UI (e.g. http://localhost:8080)",
        default="http://localhost:8080",
    )
    claude_use_external_terminal = fields.Boolean(
        "Use External Terminal",
        default=False,
        help="When enabled, opens the terminal in a new browser tab with API key "
             "authentication instead of the embedded iframe.",
    )
    claude_api_key = fields.Char(
        "API Key",
        help="Your Odoo API key for external terminal authentication. "
             "Generate one in Settings → Users → API Keys.",
    )
    claude_anthropic_api_key = fields.Char(
        "Anthropic API Key",
        help="Pre-authenticates the Claude terminal so Claude won't ask "
             "for login on start. Accepts both:\n"
             "  * sk-ant-api03-… (API billing, from the Anthropic Console)\n"
             "  * sk-ant-oat01-… (Pro / Teams / Max OAuth tokens, via "
             "claude /login → ~/.claude/credentials.json).\n"
             "Use /login inside the terminal to re-auth manually.",
    )
    claude_theme = fields.Selection(
        [
            ("github", "GitHub (Light)"),
            ("solarized-light", "Solarized Light"),
            ("one-half-light", "One Half Light"),
            ("material-light", "Material Light"),
            ("pencil-light", "Pencil Light"),
            ("tomorrow", "Tomorrow"),
            ("piatto-light", "Piatto Light"),
            ("violet-light", "Violet Light"),
            ("novel", "Novel"),
            ("dracula", "Dracula"),
            ("solarized-dark", "Solarized Dark"),
            ("one-half-dark", "One Half Dark"),
            ("material-dark", "Material Dark"),
            ("gruvbox-dark", "Gruvbox Dark"),
            ("pencil-dark", "Pencil Dark"),
            ("tomorrow-night", "Tomorrow Night"),
            ("atom", "Atom"),
            ("monokai", "Monokai"),
            ("violet-dark", "Violet Dark"),
        ],
        string="Terminal Theme",
        default="github",
        help="Color theme for the Claude Terminal.",
    )

    # ── Odoo RPC Connector ──
    claude_odoo_url = fields.Char(
        "Odoo URL",
        help="Odoo instance URL for RPC connector (e.g. http://localhost:8069)",
        default="http://localhost:8069",
    )
    claude_odoo_db = fields.Selection(
        selection="_selection_claude_odoo_db",
        string="Database",
        help="Odoo database name for RPC connector",
    )
    claude_odoo_protocol = fields.Selection(
        [("xmlrpc", "XML-RPC"), ("jsonrpc", "JSON-RPC")],
        string="Protocol",
        default="xmlrpc",
        help="XML-RPC (Odoo 8+) or JSON-RPC (Odoo 14+)",
    )
    claude_odoo_api_key = fields.Char(
        "Odoo API Key",
        help="API key for Odoo RPC authentication (Settings → Users → API Keys).",
    )

    @api.model
    def _selection_claude_odoo_db(self):
        try:
            dbs = list_dbs(force=True)
            return [(db, db) for db in sorted(dbs)]
        except Exception:
            db = self.env.cr.dbname
            return [(db, db)]

    # ── Telegram MCP ──
    claude_telegram_api_id = fields.Char(
        "API ID",
        help="Telegram API ID from my.telegram.org",
    )
    claude_telegram_api_hash = fields.Char(
        "API Hash",
        help="Telegram API Hash from my.telegram.org",
    )
    claude_telegram_phone = fields.Char(
        "Phone",
        help="Phone number with country code (e.g. +359...)",
    )
    claude_telegram_session = fields.Char(
        "Session Name",
        help="Telegram session name (default: claude_session)",
        default="claude_session",
    )

    # ── Viber MCP ──
    claude_viber_bot_token = fields.Char(
        "Bot Token",
        help="Viber Bot API token from partners.viber.com",
    )
    claude_viber_bot_name = fields.Char(
        "Bot Name",
        help="Viber bot display name",
    )
    claude_viber_webhook_url = fields.Char(
        "Webhook URL",
        help="Public HTTPS URL for Viber webhook (e.g. https://yourdomain.com/viber/webhook)",
    )

    # ── Web Session ──
    claude_web_url = fields.Char(
        "Web Session URL",
        help="URL for web session authentication (e.g. https://www.odoo.com)",
    )
    claude_web_db = fields.Char(
        "Web Session DB",
        help="Database name for web session (e.g. openerp). Leave empty to auto-detect.",
    )
    claude_web_login = fields.Char(
        "Web Session Login",
        help="Login (email) for web session authentication.",
    )
    claude_web_password = fields.Char(
        "Web Session Password",
        help="Password for web session authentication.",
    )

    # ── MCP Server ──
    claude_mcp_url = fields.Char(
        "MCP Server URL",
        help="URL of the MCP server (e.g. https://mcp.odoo-shell.space)",
        default="https://mcp.odoo-shell.space",
    )
    claude_mcp_token = fields.Char(
        "MCP API Token",
        help="API token for MCP server authentication (X-Api-Token header).",
    )
    claude_mcp_client_id = fields.Char(
        "MCP OAuth Client ID",
        help="OAuth 2.0 client ID for MCP server (optional).",
    )
    claude_mcp_api_key = fields.Char(
        "MCP API Key",
        help="Alternative API key for MCP server (optional).",
    )

    _CLAUDE_FIELDS = [
        "claude_terminal_url",
        "claude_use_external_terminal",
        "claude_api_key",
        "claude_anthropic_api_key",
        "claude_theme",
        "claude_odoo_url",
        "claude_odoo_db",
        "claude_odoo_protocol",
        "claude_odoo_api_key",
        "claude_telegram_api_id",
        "claude_telegram_api_hash",
        "claude_telegram_phone",
        "claude_telegram_session",
        "claude_web_url",
        "claude_web_db",
        "claude_web_login",
        "claude_web_password",
        "claude_mcp_url",
        "claude_mcp_token",
        "claude_mcp_client_id",
        "claude_mcp_api_key",
        "claude_viber_bot_token",
        "claude_viber_bot_name",
        "claude_viber_webhook_url",
    ]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + self._CLAUDE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + self._CLAUDE_FIELDS

    def action_test_connections(self):
        """Test all connections and show chained sticky notifications (no dialog)."""
        user = self.env.user

        def mk_ctx():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx

        # ── Test Odoo RPC ─────────────────────────────────────────────
        odoo_url = (user.claude_odoo_url or "").rstrip("/")
        odoo_db = user.claude_odoo_db or self.env.cr.dbname
        odoo_api_key = user.claude_odoo_api_key or ""
        if odoo_url and odoo_api_key:
            try:
                common = xmlrpc.client.ServerProxy(
                    f"{odoo_url}/xmlrpc/2/common", allow_none=True
                )
                uid = common.authenticate(odoo_db, user.login, odoo_api_key, {})
                if uid:
                    version = common.version().get("server_version", "")
                    odoo_status, odoo_msg = "ok", _("Connected — UID %s, Odoo %s") % (uid, version)
                else:
                    odoo_status, odoo_msg = "error", _("Authentication failed — check DB, login or API key")
            except Exception as e:
                odoo_status, odoo_msg = "error", str(e)[:200]
        else:
            odoo_status, odoo_msg = "warn", _("URL or API key not configured")

        # ── Test MCP Server ───────────────────────────────────────────
        mcp_url = (getattr(user, "claude_mcp_url", "") or "").rstrip("/")
        mcp_token = getattr(user, "claude_mcp_token", "") or ""
        if mcp_url:
            try:
                headers = {"User-Agent": "OdooClaudeTerminal/1.0"}
                if mcp_token:
                    headers["X-Api-Token"] = mcp_token
                req = urllib.request.Request(f"{mcp_url}/health", headers=headers)
                with urllib.request.urlopen(req, timeout=8, context=mk_ctx()) as resp:
                    body = resp.read(256).decode(errors="replace")
                    mcp_status, mcp_msg = "ok", _("HTTP %s — %s") % (resp.status, body[:80])
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    mcp_status, mcp_msg = "warn", _("HTTP %s — check MCP token") % e.code
                else:
                    mcp_status, mcp_msg = "error", _("HTTP %s") % e.code
            except Exception as e:
                mcp_status, mcp_msg = "error", str(e)[:200]
        else:
            mcp_status, mcp_msg = "warn", _("MCP Server URL not configured")

        # ── Test Web Session ──────────────────────────────────────────
        web_url = (getattr(user, "claude_web_url", "") or "").rstrip("/")
        web_login = getattr(user, "claude_web_login", "") or ""
        web_password = getattr(user, "claude_web_password", "") or ""
        web_db = getattr(user, "claude_web_db", "") or ""
        if web_url and web_login and web_password:
            try:
                payload = json.dumps({
                    "jsonrpc": "2.0", "method": "call", "id": 1,
                    "params": {
                        "login": web_login,
                        "password": web_password,
                        **({"db": web_db} if web_db else {}),
                    },
                }).encode()
                req = urllib.request.Request(
                    f"{web_url}/web/session/authenticate",
                    data=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "OdooClaudeTerminal/1.0"},
                )
                with urllib.request.urlopen(req, timeout=10, context=mk_ctx()) as resp:
                    result = json.loads(resp.read())
                uid = (result.get("result") or {}).get("uid")
                if uid:
                    web_status, web_msg = "ok", _("Authenticated — UID %s") % uid
                else:
                    err_msg = (result.get("error") or {}).get("data", {}).get("message", "Authentication failed")
                    web_status, web_msg = "error", err_msg[:200]
            except Exception as e:
                web_status, web_msg = "error", str(e)[:200]
        else:
            web_status, web_msg = "warn", _("URL, login or password not configured")

        # ── Test Qdrant ───────────────────────────────────────────────
        company = user.company_id
        qdrant_url = (company.claude_qdrant_url or "").rstrip("/")
        qdrant_key = company.claude_qdrant_api_key or ""
        if qdrant_url:
            try:
                headers = {"User-Agent": "OdooClaudeTerminal/1.0"}
                if qdrant_key:
                    headers["api-key"] = qdrant_key
                req = urllib.request.Request(f"{qdrant_url}/collections", headers=headers)
                with urllib.request.urlopen(req, timeout=8, context=mk_ctx()) as resp:
                    data = json.loads(resp.read())
                count = len((data.get("result") or {}).get("collections") or [])
                qdrant_status, qdrant_msg = "ok", _("Connected — %s collection(s)") % count
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    qdrant_status, qdrant_msg = "warn", _("HTTP %s — check Qdrant api-key") % e.code
                else:
                    qdrant_status, qdrant_msg = "error", _("HTTP %s") % e.code
            except Exception as e:
                qdrant_status, qdrant_msg = "error", str(e)[:200]
        else:
            qdrant_status, qdrant_msg = "warn", _("Qdrant URL not configured — AI tokenization disabled")

        # ── Test Ollama ───────────────────────────────────────────────
        ollama_url = (company.claude_ollama_url or "").rstrip("/")
        provider = company.claude_embedding_provider or "ollama"
        if provider == "ollama" and ollama_url:
            try:
                req = urllib.request.Request(
                    f"{ollama_url}/api/tags",
                    headers={"User-Agent": "OdooClaudeTerminal/1.0"},
                )
                with urllib.request.urlopen(req, timeout=8, context=mk_ctx()) as resp:
                    data = json.loads(resp.read())
                models_ = [m.get("name", "") for m in (data.get("models") or [])]
                target = company.claude_ollama_model or ""
                has_model = any(m.startswith(target) for m in models_)
                if has_model:
                    ollama_status, ollama_msg = "ok", _("Connected — %s available") % target
                else:
                    ollama_status, ollama_msg = "warn", _(
                        "Connected but model '%s' not pulled. Run: ollama pull %s"
                    ) % (target, target)
            except Exception as e:
                ollama_status, ollama_msg = "error", str(e)[:200]
        elif provider != "ollama":
            ollama_status, ollama_msg = "warn", _("Provider=%s — Ollama not used") % provider
        else:
            ollama_status, ollama_msg = "warn", _("Ollama URL not configured")

        # ── Return display_notification chain ────────────────────────────────────
        # Returning False would trigger ir.actions.act_window_close (action_service.js:1242)
        # and close the preferences dialog. Returning a display_notification action
        # object keeps the dialog open; the chain terminates when the last item has
        # no "next" key (client_actions.js returns undefined → doAction skips it).
        T = {"ok": "success", "warn": "warning", "error": "danger"}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Odoo RPC Connector"),
                "message": odoo_msg,
                "type": T.get(odoo_status, "info"),
                "sticky": True,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("MCP Server"),
                        "message": mcp_msg,
                        "type": T.get(mcp_status, "info"),
                        "sticky": True,
                        "next": {
                            "type": "ir.actions.client",
                            "tag": "display_notification",
                            "params": {
                                "title": _("Web Session"),
                                "message": web_msg,
                                "type": T.get(web_status, "info"),
                                "sticky": True,
                                "next": {
                                    "type": "ir.actions.client",
                                    "tag": "display_notification",
                                    "params": {
                                        "title": _("Qdrant (AI Tokenizer)"),
                                        "message": qdrant_msg,
                                        "type": T.get(qdrant_status, "info"),
                                        "sticky": True,
                                        "next": {
                                            "type": "ir.actions.client",
                                            "tag": "display_notification",
                                            "params": {
                                                "title": _("Ollama / Embeddings"),
                                                "message": ollama_msg,
                                                "type": T.get(ollama_status, "info"),
                                                "sticky": True,
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }

    def action_save_to_mcp(self):
        """Save this Odoo instance connection to the MCP server."""
        user = self.env.user
        mcp_url = (getattr(user, "claude_mcp_url", "") or "").rstrip("/")
        mcp_token = getattr(user, "claude_mcp_token", "") or ""
        if not mcp_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _("MCP Server URL is not configured."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        alias = self.env.cr.dbname
        payload = json.dumps({
            "name": user.name,
            "connections": {
                alias: {
                    "url": user.claude_odoo_url or "",
                    "db": user.claude_odoo_db or alias,
                    "user": user.login,
                    "api_key": user.claude_odoo_api_key or "",
                    "protocol": user.claude_odoo_protocol or "xmlrpc",
                }
            },
        }).encode()

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OdooClaudeTerminal/1.0",
        }
        if mcp_token:
            headers["X-Api-Token"] = mcp_token

        try:
            req = urllib.request.Request(
                f"{mcp_url}/api/user/connections",
                data=payload,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                result = json.loads(resp.read())
            count = result.get("count", 0)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _("Saved %s connection(s) to MCP server.") % count,
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _("MCP save failed: %s") % str(e)[:200],
                    "type": "danger",
                    "sticky": True,
                },
            }

    @api.model
    def get_claude_terminal_url(self):
        """RPC: return current user's terminal URL."""
        return self.env.user.claude_terminal_url or ""

    def action_open_anthropic_console(self):
        """Open the Anthropic Console API Keys page (for API billing).

        User creates or copies a key (``sk-ant-api03-…``) and pastes it
        into ``claude_anthropic_api_key``.
        """
        return {
            "type": "ir.actions.act_url",
            "url": "https://console.anthropic.com/settings/keys",
            "target": "new",
        }

    def action_open_claude_oauth(self):
        """Open the Claude.ai login page (for Pro / Teams / Max plans).

        After login, the OAuth token can be retrieved from the local
        ``~/.claude/credentials.json`` (as created by ``claude /login``)
        and pasted into ``claude_anthropic_api_key``.
        """
        return {
            "type": "ir.actions.act_url",
            "url": "https://claude.ai/login",
            "target": "new",
        }

    @api.model
    def notify_claude_refresh(self, payload=None):
        """Send a bus notification to refresh the user's browser view.

        Called by the MCP server (odoo_refresh tool) after creating/updating
        records so the Odoo tab auto-reloads.
        """
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "claude_terminal/refresh",
            payload or {},
        )
        return True

    @api.model
    def notify_claude_refresh_field(self, payload=None):
        """Live field-level refresh: Claude wrote specific fields on a record.

        The MCP server calls this after odoo_write() so the user's open form
        view can flash and update the specific fields that Claude changed.

        Payload format:
            {
                "kind": "field",
                "model": "sale.order",
                "res_ids": [123],
                "values": {"partner_id": 5, "note": "..."},
                "sessions": [{session_id, model, res_id, view_type}, ...]
            }
        """
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "claude_terminal/refresh_field",
            payload or {},
        )
        return True

    @api.model
    def notify_claude_refresh_list(self, payload=None):
        """Live list refresh: Claude created a new record.

        Called after odoo_create() so open list views can highlight the new
        row without a full reload.

        Payload format:
            {
                "kind": "list",
                "model": "sale.order",
                "res_ids": [456],
                "values": {...},
                "sessions": [...]
            }
        """
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "claude_terminal/refresh_list",
            payload or {},
        )
        return True

    @api.model
    def get_claude_mcp_config(self):
        """RPC: return current user's full MCP configuration for the terminal."""
        user = self.env.user
        return {
            "terminal_url": user.claude_terminal_url or "",
            "use_external": user.claude_use_external_terminal,
            "api_key": user.claude_api_key or "",
            "anthropic_api_key": user.claude_anthropic_api_key or "",
            "theme": user.claude_theme or "github",
            "odoo": {
                "url": user.claude_odoo_url or "",
                "db": user.claude_odoo_db or self.env.cr.dbname,
                "username": user.login,
                "api_key": user.claude_odoo_api_key or "",
                "protocol": user.claude_odoo_protocol or "xmlrpc",
            },
            "telegram": {
                "api_id": user.claude_telegram_api_id or "",
                "api_hash": user.claude_telegram_api_hash or "",
                "phone": user.claude_telegram_phone or "",
                "session_name": user.claude_telegram_session or "",
            },
            "web_session": {
                "url": user.claude_web_url or "",
                "db": user.claude_web_db or "",
                "login": user.claude_web_login or "",
                "password": user.claude_web_password or "",
            },
            "mcp_server": {
                "url": user.claude_mcp_url or "",
                "token": user.claude_mcp_token or "",
                "client_id": user.claude_mcp_client_id or "",
                "api_key": user.claude_mcp_api_key or "",
            },
            "viber": {
                "bot_token": user.claude_viber_bot_token or "",
                "bot_name": user.claude_viber_bot_name or "",
                "webhook_url": user.claude_viber_webhook_url or "",
            },
            "ai_tokenizer": {
                "enabled": bool(user.company_id.claude_qdrant_url),
                "qdrant_url": user.company_id.claude_qdrant_url or "",
                "qdrant_api_key": user.company_id.claude_qdrant_api_key or "",
                "collection_prefix": user.company_id.claude_qdrant_collection_prefix or "odoo_",
                "ollama_url": user.company_id.claude_ollama_url or "",
                "ollama_model": user.company_id.claude_ollama_model or "nomic-embed-text",
                "provider": user.company_id.claude_embedding_provider or "ollama",
                "embedding_api_key": user.company_id.claude_embedding_api_key or "",
            },
        }
