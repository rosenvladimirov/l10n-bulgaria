# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
