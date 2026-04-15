# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ── AI Tokenizer (Qdrant + Ollama) ──
    # Related към current company — стандартен pattern за res.config.settings.
    claude_qdrant_url = fields.Char(
        related="company_id.claude_qdrant_url",
        readonly=False,
    )
    claude_qdrant_api_key = fields.Char(
        related="company_id.claude_qdrant_api_key",
        readonly=False,
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
    )
