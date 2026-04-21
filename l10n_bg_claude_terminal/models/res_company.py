# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


# Number of days after which API keys on this company should be rotated.
# Matches common enterprise policy (90d) and Anthropic's recommendation
# for workspace keys. Exposed through ``claude_keys_needs_rotation`` so
# the settings view can raise a banner without a cron.
_KEY_MAX_AGE_DAYS = 90


class ResCompany(models.Model):
    _inherit = "res.company"

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
