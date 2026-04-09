# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import ssl
import urllib.request
import xmlrpc.client

from odoo import _, api, fields, models


def _mk_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


STATUS = [("ok", "OK"), ("warn", "Warning"), ("error", "Error"), ("skip", "Skipped")]


class ClaudeTerminalTestWizard(models.TransientModel):
    _name = "claude.terminal.test.wizard"
    _description = "Claude Terminal — Connection Test"

    # ── Odoo RPC ──────────────────────────────────────────────────────
    odoo_status = fields.Selection(STATUS, default="skip", readonly=True)
    odoo_message = fields.Char("Odoo RPC", readonly=True)

    # ── MCP Server ───────────────────────────────────────────────────
    mcp_status = fields.Selection(STATUS, default="skip", readonly=True)
    mcp_message = fields.Char("MCP Server", readonly=True)

    # ── Web Session ──────────────────────────────────────────────────
    web_status = fields.Selection(STATUS, default="skip", readonly=True)
    web_message = fields.Char("Web Session", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user = self.env.user

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
                    res["odoo_status"] = "ok"
                    res["odoo_message"] = _(
                        "Connected — UID %s, Odoo %s"
                    ) % (uid, version)
                else:
                    res["odoo_status"] = "error"
                    res["odoo_message"] = _("Authentication failed — check DB, login or API key")
            except Exception as e:
                res["odoo_status"] = "error"
                res["odoo_message"] = str(e)[:120]
        else:
            res["odoo_status"] = "warn"
            res["odoo_message"] = _("URL or API key not configured")

        # ── Test MCP Server ───────────────────────────────────────────
        mcp_url = (user.claude_mcp_url or "").rstrip("/")
        mcp_token = user.claude_mcp_token or ""
        if mcp_url:
            try:
                headers = {"User-Agent": "OdooClaudeTerminal/1.0"}
                if mcp_token:
                    headers["X-Api-Token"] = mcp_token
                req = urllib.request.Request(
                    f"{mcp_url}/health", headers=headers
                )
                with urllib.request.urlopen(req, timeout=8, context=_mk_ctx()) as resp:
                    body = resp.read(256).decode(errors="replace")
                    res["mcp_status"] = "ok"
                    res["mcp_message"] = _("HTTP %s — %s") % (resp.status, body[:60])
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    res["mcp_status"] = "warn"
                    res["mcp_message"] = _("HTTP %s — check MCP token") % e.code
                else:
                    res["mcp_status"] = "error"
                    res["mcp_message"] = _("HTTP %s") % e.code
            except Exception as e:
                res["mcp_status"] = "error"
                res["mcp_message"] = str(e)[:120]
        else:
            res["mcp_status"] = "warn"
            res["mcp_message"] = _("MCP Server URL not configured")

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
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "OdooClaudeTerminal/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=10, context=_mk_ctx()) as resp:
                    result = json.loads(resp.read())
                uid = (result.get("result") or {}).get("uid")
                if uid:
                    res["web_status"] = "ok"
                    res["web_message"] = _("Authenticated — UID %s") % uid
                else:
                    err_msg = (
                        (result.get("error") or {})
                        .get("data", {})
                        .get("message", "Authentication failed")
                    )
                    res["web_status"] = "error"
                    res["web_message"] = err_msg[:120]
            except Exception as e:
                res["web_status"] = "error"
                res["web_message"] = str(e)[:120]
        else:
            res["web_status"] = "warn"
            res["web_message"] = _("URL, login or password not configured")

        return res
