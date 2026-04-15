# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import ssl
import urllib.request
import urllib.error

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class AiEmbeddingProvider(models.AbstractModel):
    """Stateless helper that turns text into vectors.

    Configuration read from self.env.company (AI Tokenizer settings):
      - claude_embedding_provider: ollama | openai | voyage | anthropic
      - claude_ollama_url / claude_ollama_model
      - claude_embedding_api_key (for paid providers)
    """

    _name = "ai.embedding.provider"
    _description = "AI Tokenizer — Embedding Provider"

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    @api.model
    def embed(self, texts, company=None):
        """Return a list of vectors (list[float]) — one per input text.

        Raises UserError with human-readable cause on misconfiguration or
        upstream failure. Callers should treat any exception as terminal
        for the batch and mark the composite documents as state='error'.
        """
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []

        company = (company or self.env.company).sudo()
        provider = company.claude_embedding_provider or "ollama"

        if provider == "ollama":
            return self._embed_ollama(texts, company)
        if provider == "openai":
            return self._embed_openai(texts, company)
        if provider == "voyage":
            return self._embed_voyage(texts, company)
        if provider == "anthropic":
            # Anthropic has no public embedding endpoint at present;
            # fall back to Voyage (recommended by Anthropic).
            return self._embed_voyage(texts, company)
        raise UserError(f"Unknown embedding provider: {provider}")

    @api.model
    def vector_size(self, company=None):
        """Return the dimensionality of vectors for the current provider.

        Used when creating the Qdrant collection. A cheap sentinel embed
        call is used if the model is unknown — cached on the company's
        config is NOT attempted here to keep the call stateless.
        """
        company = (company or self.env.company).sudo()
        provider = company.claude_embedding_provider or "ollama"
        model = (company.claude_ollama_model or "nomic-embed-text").lower()

        # Static table for well-known models.
        known = {
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "voyage-3": 1024,
            "voyage-3-large": 1024,
        }
        for key, dim in known.items():
            if model.startswith(key):
                return dim
        if provider == "openai":
            return 1536
        if provider == "voyage":
            return 1024
        # Fallback — single probe.
        vec = self.embed(["__probe__"], company=company)
        if not vec or not vec[0]:
            raise UserError("Could not determine embedding dimensionality.")
        return len(vec[0])

    # ──────────────────────────────────────────────────────────
    # Provider implementations
    # ──────────────────────────────────────────────────────────

    def _embed_ollama(self, texts, company):
        url = (company.claude_ollama_url or "").rstrip("/")
        model = company.claude_ollama_model or "nomic-embed-text"
        if not url:
            raise UserError("Ollama URL is not configured.")
        # Ollama's /api/embed (plural) accepts input: str | list[str]
        payload = json.dumps({"model": model, "input": texts}).encode()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OdooAiTokenizer/1.0",
        }
        # Optional auth (for proxied Ollama — e.g. mcp.../ollama with MCP token)
        api_key = (company.sudo().claude_embedding_api_key or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(
            f"{url}/api/embed",
            data=payload,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx()) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            raise UserError(f"Ollama HTTP {e.code}: {body}") from None
        except Exception as e:
            raise UserError(f"Ollama error: {e}") from None

        vectors = data.get("embeddings") or []
        if not vectors and "embedding" in data:
            # /api/embeddings (legacy, singular) returns a single vector
            vectors = [data["embedding"]]
        if len(vectors) != len(texts):
            raise UserError(
                f"Ollama returned {len(vectors)} vectors for {len(texts)} inputs"
            )
        return vectors

    def _embed_openai(self, texts, company):
        api_key = company.claude_embedding_api_key or ""
        if not api_key:
            raise UserError("OpenAI API key is not configured.")
        model = company.claude_ollama_model or "text-embedding-3-small"
        if model.startswith("nomic") or model.startswith("mxbai"):
            # User likely didn't update the model — fall back to OpenAI default.
            model = "text-embedding-3-small"
        payload = json.dumps({"model": model, "input": texts}).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "OdooAiTokenizer/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx()) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            raise UserError(f"OpenAI HTTP {e.code}: {body}") from None
        except Exception as e:
            raise UserError(f"OpenAI error: {e}") from None
        return [item["embedding"] for item in (data.get("data") or [])]

    def _embed_voyage(self, texts, company):
        api_key = company.claude_embedding_api_key or ""
        if not api_key:
            raise UserError("Voyage API key is not configured.")
        model = company.claude_ollama_model or "voyage-3"
        if model.startswith("nomic") or model.startswith("mxbai"):
            model = "voyage-3"
        payload = json.dumps({
            "model": model,
            "input": texts,
            "input_type": "document",
        }).encode()
        req = urllib.request.Request(
            "https://api.voyageai.com/v1/embeddings",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "OdooAiTokenizer/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx()) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            raise UserError(f"Voyage HTTP {e.code}: {body}") from None
        except Exception as e:
            raise UserError(f"Voyage error: {e}") from None
        return [item["embedding"] for item in (data.get("data") or [])]
