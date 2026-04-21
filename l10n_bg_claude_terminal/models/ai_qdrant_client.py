# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import ssl
import urllib.error
import urllib.request
import uuid

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class AiQdrantClient(models.AbstractModel):
    """Minimal Qdrant REST client — covers collection/point lifecycle.

    Config from env.company: claude_qdrant_url, claude_qdrant_api_key,
    claude_qdrant_collection_prefix.
    """

    _name = "ai.qdrant.client"
    _description = "AI Tokenizer — Qdrant REST Client"

    # ──────────────────────────────────────────────────────────
    # Low-level helpers
    # ──────────────────────────────────────────────────────────

    def _base_url(self, company=None):
        company = company or self.env.company
        url = (company.sudo().claude_qdrant_url or "").rstrip("/")
        if not url:
            raise UserError("Qdrant URL is not configured (Settings → AI Tokenizer).")
        return url

    def _headers(self, company=None):
        company = company or self.env.company
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OdooAiTokenizer/1.0",
        }
        # sudo() because claude_qdrant_api_key has groups="base.group_system"
        key = company.sudo().claude_qdrant_api_key or ""
        if key:
            headers["api-key"] = key
        return headers

    def _request(self, method, path, body=None, company=None, timeout=30):
        url = self._base_url(company) + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self._headers(company))
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            raise UserError(f"Qdrant {method} {path} → HTTP {e.code}: {msg}") from None
        except Exception as e:
            raise UserError(f"Qdrant {method} {path} failed: {e}") from None
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw.decode(errors="replace")}

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    @api.model
    def collection_name(self, company=None):
        company = company or self.env.company
        prefix = company.sudo().claude_qdrant_collection_prefix or "odoo_"
        return f"{prefix}{self.env.cr.dbname}"

    @api.model
    def ensure_collection(self, vector_size, company=None):
        """Create the per-DB collection if it does not exist.

        Configures payload indexes on model/res_id/company_id/view_type
        so semantic search with filters remains fast.
        """
        name = self.collection_name(company)
        existing = self._request("GET", f"/collections/{name}/exists", company=company)
        if (existing.get("result") or {}).get("exists"):
            return name

        self._request("PUT", f"/collections/{name}", body={
            "vectors": {"size": int(vector_size), "distance": "Cosine"},
        }, company=company)

        for field, schema in (
            ("model", "keyword"),
            ("res_id", "integer"),
            ("company_id", "integer"),
            ("view_type", "keyword"),
            ("db_name", "keyword"),
        ):
            self._request("PUT", f"/collections/{name}/index", body={
                "field_name": field, "field_schema": schema,
            }, company=company)
        _logger.info("ai.qdrant.client: created collection %s (dim=%s)", name, vector_size)
        return name

    @api.model
    def upsert_point(self, point_id, vector, payload, company=None):
        """Insert or update a single point.

        point_id must be a UUID string or an integer — Qdrant rejects other shapes.
        Generates a UUID automatically if point_id is falsy.
        """
        name = self.collection_name(company)
        pid = point_id or str(uuid.uuid4())
        body = {"points": [{"id": pid, "vector": vector, "payload": payload or {}}]}
        self._request("PUT", f"/collections/{name}/points?wait=true", body=body, company=company)
        return pid

    @api.model
    def delete_point(self, point_id, company=None):
        if not point_id:
            return False
        name = self.collection_name(company)
        self._request("POST", f"/collections/{name}/points/delete?wait=true", body={
            "points": [point_id],
        }, company=company)
        return True

    @api.model
    def search(self, vector, limit=5, score_threshold=0.0, filters=None, company=None):
        """Return the Qdrant search result list (as shipped by Qdrant).

        Multi-tenant guardrail (Gap 4.6): the collection already scopes
        to (prefix × db_name), so cross-database leakage is impossible
        by construction. Within a single database every point carries a
        ``company_id`` payload; we auto-inject a ``must`` clause pinning
        it to the effective company unless the caller explicitly opted
        out via ``filters={"_skip_company_guard": True, ...}``. Prevents
        accidental cross-company retrieval if the caller forgets the
        filter (which is how information leaks happen in practice).
        """
        name = self.collection_name(company)
        filters = filters or {}
        skip_guard = filters.pop("_skip_company_guard", False)
        eff_company = company or self.env.company
        if not skip_guard and eff_company:
            must = list(filters.get("must") or [])
            has_company_filter = any(
                isinstance(c, dict)
                and (c.get("key") == "company_id"
                     or "company_id" in str(c.get("key") or ""))
                for c in must
            )
            if not has_company_filter:
                must.append({
                    "key": "company_id",
                    "match": {"value": int(eff_company.id)},
                })
                filters["must"] = must
                _logger.debug(
                    "ai.qdrant.client: auto-injected company_id=%s guard "
                    "on search (collection=%s)", eff_company.id, name,
                )
        body = {
            "vector": vector,
            "limit": int(limit),
            "with_payload": True,
            "score_threshold": float(score_threshold),
        }
        if filters:
            body["filter"] = filters
        data = self._request("POST", f"/collections/{name}/points/search", body=body, company=company)
        return data.get("result") or []
