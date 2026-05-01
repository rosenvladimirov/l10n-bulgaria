# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ── MCP Server (company-wide defaults) ──
    claude_mcp_url = fields.Char(
        related="company_id.claude_mcp_url",
        readonly=False,
    )
    claude_mcp_token = fields.Char(
        related="company_id.claude_mcp_token",
        readonly=False,
        groups="base.group_system",
    )
    claude_mcp_client_id = fields.Char(
        related="company_id.claude_mcp_client_id",
        readonly=False,
    )
    claude_mcp_api_key = fields.Char(
        related="company_id.claude_mcp_api_key",
        readonly=False,
        groups="base.group_system",
    )
    claude_anthropic_key_synced_at = fields.Datetime(
        related="company_id.claude_anthropic_key_synced_at",
        readonly=True,
        groups="base.group_system",
    )
    claude_embedding_api_key_display = fields.Char(
        "Anthropic API Key (stored)",
        related="company_id.claude_embedding_api_key",
        readonly=True,
        groups="base.group_system",
    )

    def action_reload_anthropic_key(self):
        """Proxy to res.company.action_reload_anthropic_key."""
        self.ensure_one()
        return self.company_id.action_reload_anthropic_key()

    # ── AI Tokenizer (Qdrant + Ollama) ──
    # Related към current company — стандартен pattern за res.config.settings.
    claude_qdrant_url = fields.Char(
        related="company_id.claude_qdrant_url",
        readonly=False,
    )
    claude_qdrant_api_key = fields.Char(
        related="company_id.claude_qdrant_api_key",
        readonly=False,
        groups="base.group_system",
    )
    claude_qdrant_collection_prefix = fields.Char(
        related="company_id.claude_qdrant_collection_prefix",
        readonly=False,
    )
    claude_ollama_url = fields.Char(
        related="company_id.claude_ollama_url",
        readonly=False,
    )
    claude_ollama_model = fields.Char(
        related="company_id.claude_ollama_model",
        readonly=False,
    )
    claude_embedding_provider = fields.Selection(
        related="company_id.claude_embedding_provider",
        readonly=False,
    )
    claude_embedding_api_key = fields.Char(
        related="company_id.claude_embedding_api_key",
        readonly=False,
        groups="base.group_system",
    )

    # ── API key rotation tracking (Gap 4.7) ──
    claude_keys_rotated_at = fields.Datetime(
        related="company_id.claude_keys_rotated_at",
        readonly=True,
        groups="base.group_system",
    )
    claude_keys_age_days = fields.Integer(
        related="company_id.claude_keys_age_days",
        readonly=True,
        groups="base.group_system",
    )
    claude_keys_needs_rotation = fields.Boolean(
        related="company_id.claude_keys_needs_rotation",
        readonly=True,
        groups="base.group_system",
    )

    def action_mark_keys_rotated(self):
        """Proxy to res.company.action_mark_keys_rotated for the form button."""
        self.ensure_one()
        return self.company_id.action_mark_keys_rotated()
