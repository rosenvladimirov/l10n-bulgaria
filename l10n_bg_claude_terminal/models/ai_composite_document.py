# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AiCompositeDocument(models.Model):
    _name = "ai.composite.document"
    _description = "AI Tokenizer — Composite Document"
    _order = "write_date desc"
    _rec_name = "display_name"

    registry_id = fields.Many2one(
        "ai.view.registry",
        string="Registry Entry",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_name = fields.Char(
        related="registry_id.model_name",
        store=True,
        index=True,
    )
    view_type = fields.Selection(
        related="registry_id.view_type",
        store=True,
    )
    res_id = fields.Integer(
        string="Record ID",
        required=True,
        index=True,
    )
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )
    company_id = fields.Many2one("res.company", string="Company", index=True)
    db_name = fields.Char(string="Database", index=True)
    document_text = fields.Text(string="Document Text")
    token_count = fields.Integer(string="Tokens (est.)")
    qdrant_point_id = fields.Char(string="Qdrant Point UUID")
    source_write_date = fields.Datetime(
        string="Source write_date",
        help="write_date of source record at last tokenization time.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("tokenized", "Tokenized"),
            ("indexed", "Indexed"),
            ("stale", "Stale"),
            ("error", "Error"),
        ],
        string="State",
        default="draft",
        required=True,
        index=True,
    )
    error_message = fields.Text(string="Last Error")

    _uniq_doc = models.Constraint(
        "UNIQUE(registry_id, res_id)",
        "A composite document already exists for this registry/record.",
    )

    @api.depends("model_name", "res_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.model_name or '?'}#{rec.res_id or 0}"

    def action_mark_stale(self):
        self.write({"state": "stale"})
        return True

    # ──────────────────────────────────────────────────────────
    # Tokenization pipeline
    # ──────────────────────────────────────────────────────────

    def action_tokenize_and_index(self):
        """Build the composite text, embed it, and upsert to Qdrant.

        Sets state='indexed' on success, 'error' on any failure.
        """
        self.ensure_one()
        Builder = self.env["ai.document.builder"]
        Embed = self.env["ai.embedding.provider"]
        Qdrant = self.env["ai.qdrant.client"]
        try:
            registry = self.registry_id
            if not registry or not registry.active:
                raise ValueError("Registry entry missing or archived")
            Model = self.env.get(self.model_name)
            if Model is None:
                raise ValueError(f"Model {self.model_name} not installed")
            record = self.env[self.model_name].browse(self.res_id)
            if not record.exists():
                # Source vanished — purge the Qdrant point.
                if self.qdrant_point_id:
                    try:
                        Qdrant.delete_point(self.qdrant_point_id)
                    except Exception:
                        pass
                self.unlink()
                return True

            text, token_count = Builder.build(registry, record)
            vectors = Embed.embed([text])
            if not vectors:
                raise ValueError("Embedding returned no vectors")
            vector = vectors[0]
            Qdrant.ensure_collection(len(vector))
            payload = {
                "model": self.model_name,
                "res_id": self.res_id,
                "view_type": self.view_type,
                "company_id": self.company_id.id or 0,
                "db_name": self.db_name or self.env.cr.dbname,
                "display_name": record.display_name,
                "document_text": text,
                "token_count": token_count,
                "write_date": (
                    record.write_date.isoformat() if record.write_date else None
                ),
            }
            point_id = Qdrant.upsert_point(self.qdrant_point_id, vector, payload)
            self.write({
                "document_text": text,
                "token_count": token_count,
                "qdrant_point_id": point_id,
                "source_write_date": record.write_date or False,
                "state": "indexed",
                "error_message": False,
            })
            return True
        except Exception as exc:
            _logger.exception("ai.composite.document#%s tokenize failed", self.id)
            self.write({
                "state": "error",
                "error_message": str(exc)[:2000],
            })
            return False

    @api.model
    def get_status_for_record(self, model_name, res_id, view_type="form"):
        """RPC — called by the OWL status widget.

        Returns a lightweight status dict so the frontend can render a badge
        without pulling the full document text.
        """
        if not self.env["ai.view.registry"]._is_enabled():
            return {"enabled": False}
        doc = self.sudo().search([
            ("model_name", "=", model_name),
            ("res_id", "=", res_id),
            ("view_type", "=", view_type),
        ], limit=1)
        if not doc:
            return {"enabled": True, "state": "missing", "token_count": 0}

        # Staleness: compare write_date of source record with source_write_date
        state = doc.state
        if state == "indexed":
            Model = self.env.get(model_name)
            if Model is not None:
                source = self.env[model_name].sudo().browse(res_id)
                if source.exists() and doc.source_write_date and source.write_date:
                    if source.write_date > doc.source_write_date:
                        state = "stale"
        return {
            "enabled": True,
            "document_id": doc.id,
            "state": state,
            "token_count": doc.token_count,
            "updated": doc.write_date.isoformat() if doc.write_date else False,
            "error": doc.error_message or False,
        }

    def action_open_source(self):
        self.ensure_one()
        if not (self.model_name and self.res_id):
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.model_name,
            "res_id": self.res_id,
            "views": [(False, "form")],
            "target": "current",
        }

    # ──────────────────────────────────────────────────────────
    # Semantic search (Qdrant)
    # ──────────────────────────────────────────────────────────

    @api.model
    def search_similar(self, query, model_name=None, view_type=None,
                       limit=10, score_threshold=0.0, company_id=None):
        """High-level semantic search.

        Embed `query` with the configured provider, search Qdrant filtered
        by model/view_type/company/db, return a clean list of hits.

        Parameters
        ----------
        query : str          — natural-language query string
        model_name : str     — restrict to records of one model (optional)
        view_type : str      — restrict to a view type (default: any)
        limit : int          — max hits (default 10)
        score_threshold : float — minimum cosine similarity (default 0)
        company_id : int     — restrict to one company (optional)

        Returns
        -------
        list[dict] — each hit:
            {
                "model": "res.partner",
                "res_id": 42,
                "display_name": "Tesla SA",
                "score": 0.87,
                "snippet": "first 240 chars of document_text",
                "view_type": "form",
                "document_id": 1234,
            }
        """
        if not self.env["ai.view.registry"]._is_enabled():
            return []
        if not query or not query.strip():
            return []

        Embed = self.env["ai.embedding.provider"]
        Qdrant = self.env["ai.qdrant.client"]

        vectors = Embed.embed([query])
        if not vectors:
            return []
        vector = vectors[0]

        # Build Qdrant payload filter (must clauses).
        must = [{"key": "db_name", "match": {"value": self.env.cr.dbname}}]
        if model_name:
            must.append({"key": "model", "match": {"value": model_name}})
        if view_type:
            must.append({"key": "view_type", "match": {"value": view_type}})
        if company_id:
            must.append({"key": "company_id", "match": {"value": int(company_id)}})
        filters = {"must": must}

        raw_hits = Qdrant.search(
            vector,
            limit=int(limit),
            score_threshold=float(score_threshold),
            filters=filters,
        )

        results = []
        for hit in raw_hits:
            payload = hit.get("payload") or {}
            text = payload.get("document_text") or ""
            results.append({
                "model": payload.get("model"),
                "res_id": payload.get("res_id"),
                "view_type": payload.get("view_type"),
                "display_name": payload.get("display_name"),
                "company_id": payload.get("company_id") or None,
                "score": hit.get("score"),
                "snippet": (text[:240] + "…") if len(text) > 240 else text,
                "qdrant_point_id": hit.get("id"),
            })
        return results

    # ──────────────────────────────────────────────────────────
    # Cron entry point — re-index stale/draft/error documents
    # ──────────────────────────────────────────────────────────

    @api.model
    def cron_reindex_stale(self, batch_size=50):
        """Process up to `batch_size` documents needing (re-)indexing.

        Picks documents in state stale|draft|error belonging to *active*
        registry entries; calls action_tokenize_and_index() one by one.

        Designed for the nightly `ir.cron`. Counts are logged but no
        exception escapes — single-document failures stay isolated to
        their state='error' row.
        """
        if not self.env["ai.view.registry"]._is_enabled():
            _logger.info("ai.composite.document.cron: AI tokenization disabled, skipping")
            return 0
        domain = [
            ("state", "in", ("stale", "draft", "error")),
            ("registry_id.active", "=", True),
        ]
        docs = self.search(domain, limit=int(batch_size or 50), order="write_date asc")
        ok, failed = 0, 0
        for doc in docs:
            try:
                if doc.action_tokenize_and_index():
                    ok += 1
                else:
                    failed += 1
            except Exception:  # belt-and-braces; method already swallows
                _logger.exception("cron_reindex_stale unexpected error on %s", doc.id)
                failed += 1
            # Commit per document so partial progress survives a crash.
            self.env.cr.commit()
        _logger.info(
            "ai.composite.document.cron_reindex_stale: %s ok, %s failed (batch=%s)",
            ok, failed, batch_size,
        )
        return ok

    @api.model
    def collection_stats(self):
        """Return basic stats about the per-DB Qdrant collection.

        Useful for both the OWL status widget and the MCP `qdrant_collection_info`
        tool. Returns {} when AI tokenization is disabled.
        """
        if not self.env["ai.view.registry"]._is_enabled():
            return {"enabled": False}
        Qdrant = self.env["ai.qdrant.client"]
        name = Qdrant.collection_name()
        try:
            info = Qdrant._request("GET", f"/collections/{name}")
        except Exception as exc:
            return {"enabled": True, "error": str(exc)[:200]}
        result = (info.get("result") or {})
        config = (result.get("config") or {}).get("params", {}) or {}
        vectors = config.get("vectors") or {}
        # Local count from Odoo for cross-check.
        odoo_count = self.search_count([("state", "=", "indexed")])
        return {
            "enabled": True,
            "collection": name,
            "vector_size": vectors.get("size"),
            "distance": vectors.get("distance"),
            "qdrant_points": result.get("points_count"),
            "qdrant_indexed_vectors": result.get("indexed_vectors_count"),
            "odoo_indexed_documents": odoo_count,
            "status": result.get("status"),
        }
