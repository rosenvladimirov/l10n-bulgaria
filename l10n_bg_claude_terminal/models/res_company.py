# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import ssl
import urllib.request

from odoo import _, api, fields, models
from odoo.exceptions import UserError


# Number of days after which API keys on this company should be rotated.
# Matches common enterprise policy (90d) and Anthropic's recommendation
# for workspace keys. Exposed through ``claude_keys_needs_rotation`` so
# the settings view can raise a banner without a cron.
_KEY_MAX_AGE_DAYS = 90


class ResCompany(models.Model):
    _inherit = "res.company"

    # ── MCP Server (global / company-wide) ──
    claude_mcp_url = fields.Char(
        "MCP Server URL",
        default="https://mcp.odoo-shell.space",
        help="Default MCP server for all users of this company. "
             "Individual users can override in their preferences.",
    )
    claude_mcp_token = fields.Char(
        "MCP API Token",
        groups="base.group_system",
        help="API token for MCP server (X-Api-Token header). "
             "Visible only to administrators.",
    )
    claude_mcp_client_id = fields.Char(
        "MCP OAuth Client ID",
        help="OAuth 2.0 client ID for MCP server (optional).",
    )
    claude_mcp_api_key = fields.Char(
        "MCP API Key",
        groups="base.group_system",
        help="Alternative API key for MCP server (optional). "
             "Visible only to administrators.",
    )
    claude_anthropic_key_synced_at = fields.Datetime(
        "Anthropic Key Last Synced",
        readonly=True,
        groups="base.group_system",
        help="When the ANTHROPIC_API_KEY was last pulled from the MCP server.",
    )

    def action_reload_anthropic_key(self):
        """Pull ANTHROPIC_API_KEY from the MCP server and store it as the
        embedding API key on this company.  Called from Settings and from
        the per-user 'Test Connections' flow."""
        def _mk_ctx():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx

        results = []
        for rec in self:
            mcp_url = (rec.claude_mcp_url or "").rstrip("/")
            mcp_token = rec.claude_mcp_token or ""
            if not mcp_url:
                raise UserError(_("MCP Server URL is not configured for this company."))
            if not mcp_token:
                raise UserError(_("MCP API Token is not configured for this company."))
            try:
                req = urllib.request.Request(
                    f"{mcp_url}/api/config/ai_keys",
                    headers={
                        "X-Api-Token": mcp_token,
                        "User-Agent": "OdooClaudeTerminal/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=10, context=_mk_ctx()) as resp:
                    data = json.loads(resp.read())
            except Exception as e:
                raise UserError(
                    _("Cannot reach MCP server at %s: %s") % (mcp_url, str(e))
                ) from e
            ak = data.get("anthropic_api_key", "")
            if not ak:
                raise UserError(
                    _("MCP server returned an empty Anthropic API key. "
                      "Set ANTHROPIC_API_KEY in the MCP server environment first.")
                )
            rec.sudo().write({
                "claude_embedding_api_key": ak,
                "claude_anthropic_key_synced_at": fields.Datetime.now(),
            })
            results.append(rec.name)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Anthropic key synced"),
                "message": _("ANTHROPIC_API_KEY saved from MCP server for: %s")
                           % ", ".join(results),
                "type": "success",
                "sticky": False,
            },
        }

    # ── AI Tokenizer (Qdrant + Ollama) ──
    # Преместено от res.users (v1.21.0) — инфраструктурен конфиг на ниво фирма.
    claude_qdrant_url = fields.Char(
        "Qdrant URL",
        help="Qdrant vector DB endpoint (e.g. http://localhost:6333). "
             "Leave empty to disable AI tokenization.",
    )
    claude_qdrant_api_key = fields.Char(
        "Qdrant API Key",
        groups="base.group_system",
        help="Optional API key for Qdrant (if running with QDRANT__SERVICE__API_KEY). "
             "Visible only to administrators.",
    )
    claude_qdrant_collection_prefix = fields.Char(
        "Qdrant Collection Prefix",
        default="odoo_",
        help="Prefix for per-database collections. Final name: <prefix><db_name>.",
    )
    claude_ollama_url = fields.Char(
        "Ollama URL",
        default="http://localhost:11434",
        help="Ollama endpoint for local embeddings (e.g. http://localhost:11434).",
    )
    claude_ollama_model = fields.Char(
        "Embedding Model",
        default="nomic-embed-text",
        help="Ollama model for embeddings. Common: nomic-embed-text (768d), "
             "mxbai-embed-large (1024d).",
    )
    claude_embedding_provider = fields.Selection(
        [
            ("ollama", "Ollama (local)"),
            ("openai", "OpenAI"),
            ("voyage", "Voyage AI"),
            ("anthropic", "Anthropic"),
        ],
        string="Embedding Provider",
        default="ollama",
        help="Backend used to generate vector embeddings.",
    )
    claude_embedding_api_key = fields.Char(
        "Embedding API Key",
        groups="base.group_system",
        help="Auth token sent as 'Authorization: Bearer ...' to the embedding endpoint. "
             "Required for paid providers (OpenAI/Voyage/Anthropic). "
             "Also used for proxied Ollama (e.g. MCP server at https://mcp.odoo-shell.space/ollama — "
             "set this to the MCP_SECRET_TOKEN). Leave empty for direct Ollama without auth. "
             "Visible only to administrators.",
    )

    # ── API key rotation tracking (Gap 4.7) ──
    # Tracks when the operator last marked *all* AI-related secrets on
    # this company as freshly rotated. A banner lights up when we pass
    # the max age (90d by default) — nobody is blocked; it is an
    # advisory nag so credentials don't drift forever.
    claude_keys_rotated_at = fields.Datetime(
        string="AI Keys Last Rotated At",
        groups="base.group_system",
        help="Set when an administrator confirms all AI/integration "
             "secrets (Qdrant, embedding provider, MCP token, Viber, "
             "Telegram hashes) were just rotated. Use the 'I rotated "
             "the keys' button in Settings after you actually updated "
             "them in their respective consoles.",
    )
    claude_keys_age_days = fields.Integer(
        string="Days Since Rotation",
        compute="_compute_claude_keys_rotation",
        groups="base.group_system",
    )
    claude_keys_needs_rotation = fields.Boolean(
        string="Keys Need Rotation",
        compute="_compute_claude_keys_rotation",
        groups="base.group_system",
    )

    @api.depends("claude_keys_rotated_at")
    def _compute_claude_keys_rotation(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.claude_keys_rotated_at:
                # Never rotated → treat as stale so admins see the nag
                # on fresh installs and schedule the first rotation.
                rec.claude_keys_age_days = 9999
                rec.claude_keys_needs_rotation = True
                continue
            delta = now - rec.claude_keys_rotated_at
            age = max(0, delta.days)
            rec.claude_keys_age_days = age
            rec.claude_keys_needs_rotation = age >= _KEY_MAX_AGE_DAYS

    def action_mark_keys_rotated(self):
        """Record that all AI secrets were just rotated.

        Call this from the Settings form button AFTER you actually
        rotated the keys in their upstream consoles (Qdrant, OpenAI,
        Voyage, Anthropic workspace, MCP, etc.) and pasted the new
        values. Resets the age counter to 0 and clears the banner.
        """
        now = fields.Datetime.now()
        for rec in self:
            rec.sudo().claude_keys_rotated_at = now
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("AI keys marked rotated"),
                "message": _(
                    "Next rotation reminder in %s days."
                ) % _KEY_MAX_AGE_DAYS,
                "type": "success",
                "sticky": False,
            },
        }
