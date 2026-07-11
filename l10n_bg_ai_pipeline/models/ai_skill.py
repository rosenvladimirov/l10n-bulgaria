# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Matches [xx_YY]...[/xx_YY] language blocks used in skill
# description/content — same convention as the Odoo 20 _explanation
# backport in l10n_bg_claude_terminal.
_LANG_MARKER_RE = re.compile(r"\[/?[a-z]{2}_[A-Z]{2}\]")


def _strip_lang_markers(text):
    """Remove all ``[xx_YY]`` open/close tags from ``text``.

    Used when the skill's ``language`` is ``all`` — we still want the
    semantic vector to be free of the marker noise.
    """
    if not text:
        return text
    return _LANG_MARKER_RE.sub("", text).strip()


class AiQdrantSkillsClient(models.AbstractModel):
    """Skills Qdrant client — lives in its own collection so document
    embeddings and skill description embeddings never mix.
    """

    _name = "ai.qdrant.skills.client"
    _inherit = "ai.qdrant.client"
    _description = "AI Tokenizer — Qdrant REST Client (skills collection)"

    @api.model
    def collection_name(self, company=None):
        base = super().collection_name(company)
        return f"{base}_skills"


class AiSkill(models.Model):
    """Anthropic-style Agent Skill stored in Odoo.

    Three disclosure levels, mirroring the upstream pattern:
      * L1 — ``description`` (always indexed in Qdrant for semantic match)
      * L2 — ``content`` (loaded into LLM context only when the skill is
        matched for the current document)
      * L3 — ``resources_model`` + ``resources_method`` (callable run on
        demand, e.g. to post an invoice, emit an NRA file, etc.)

    Skills declare *where* they inject themselves via the one-to-many
    ``pipeline_step_ids`` — steps which become active only for documents
    matched against this skill.
    """

    _name = "ai.skill"
    _description = "AI Skill (Anthropic-style, Odoo-hosted)"
    _order = "priority desc, name"

    # ── Level 1 metadata ───────────────────────────────────────
    name = fields.Char(required=True, index=True, help=(
        "Technical identifier, kebab-case. Mirrors Anthropic SKILL.md "
        "frontmatter 'name'."
    ))
    description = fields.Text(required=True, help=(
        "Trigger hint for semantic matching. Describe *what* the skill "
        "does and *when* it should activate. Indexed in Qdrant."
    ))
    display_name_override = fields.Char(string="Display Name")

    # ── Level 2 body ───────────────────────────────────────────
    content = fields.Text(help=(
        "Procedural instructions loaded into the LLM prompt when the "
        "skill is matched. Mirrors the body of SKILL.md."
    ))

    # ── Level 3 executable ─────────────────────────────────────
    resources_model = fields.Char(help=(
        "Odoo model whose method is invoked when the skill fires "
        "(e.g. 'account.move')."
    ))
    resources_method = fields.Char(help=(
        "Method name on resources_model — signature: (self, ctx) → ctx."
    ))

    # ── Targeting / provenance ─────────────────────────────────
    language = fields.Selection(
        selection="_sel_language",
        default="all",
        help="Which user language this skill applies to. 'all' = any.",
    )
    priority = fields.Integer(default=10)
    module = fields.Char(help="Source module — set automatically from XML id.")
    active = fields.Boolean(default=True)

    # ── Injection ──────────────────────────────────────────────
    pipeline_step_ids = fields.One2many(
        "ai.pipeline.step",
        "skill_id",
        string="Injected Steps",
        help="Pipeline steps that activate when this skill matches.",
    )
    pipeline_step_count = fields.Integer(
        compute="_compute_pipeline_step_count",
    )

    # ── Level 1 tokenization state ─────────────────────────────
    state = fields.Selection([
        ("draft", "Draft"),
        ("indexed", "Indexed"),
        ("stale", "Stale"),
        ("error", "Error"),
    ], default="draft", index=True)
    qdrant_point_id = fields.Char(copy=False)
    error_message = fields.Text(readonly=True)

    _sql_constraints = [
        ("ai_skill_name_uniq", "unique(name)", "Skill name must be unique."),
    ]

    # ── Selection helpers ──────────────────────────────────────
    @api.model
    def _sel_language(self):
        langs = self.env["res.lang"].search([])
        return [("all", _("All languages"))] + [
            (l.code, l.name) for l in langs
        ]

    @api.depends("pipeline_step_ids")
    def _compute_pipeline_step_count(self):
        for rec in self:
            rec.pipeline_step_count = len(rec.pipeline_step_ids)

    # ── L1 indexing ────────────────────────────────────────────
    def _embeddable_description(self):
        """Return the description body to feed into the embedding call.

        Strips ``[xx_YY]`` markers so the semantic vector reflects the
        actual prose.  If ``language`` is a concrete Odoo lang and the
        backported ``_extract_lang`` helper is installed, the matching
        block is isolated — that way bilingual description authors can
        still tokenize just the tenant's language.
        """
        self.ensure_one()
        text = self.description or ""
        if self.language and self.language != "all":
            try:
                from odoo.addons.l10n_bg_claude_terminal.models.ir_model \
                    import _extract_lang
            except ImportError:
                _extract_lang = None
            if _extract_lang is not None:
                extracted = _extract_lang(text, self.language)
                if extracted:
                    return extracted
        # Either language='all' or extractor unavailable: strip markers
        # so the vector is not polluted with Anthropic-style tags.
        return _strip_lang_markers(text)

    def action_tokenize_description(self):
        """Embed ``description`` and upsert into the skills collection.

        The document itself is tiny (~100–500 tokens); this is the
        equivalent of Anthropic's always-loaded metadata layer.
        """
        Embed = self.env["ai.embedding.provider"]
        Qdrant = self.env["ai.qdrant.skills.client"]
        for rec in self:
            try:
                text = rec._embeddable_description()
                if not text:
                    raise UserError(_(
                        "Skill %s has no description for language %s."
                    ) % (rec.name, rec.language))
                vectors = Embed.embed([text])
                if not vectors:
                    raise UserError(_("Embedding provider returned no vectors."))
                vec = vectors[0]
                Qdrant.ensure_collection(len(vec))
                payload = {
                    "model": "ai.skill",
                    "res_id": rec.id,
                    "skill_name": rec.name,
                    "language": rec.language,
                    "priority": rec.priority,
                    "module": rec.module or "",
                    "db_name": self.env.cr.dbname,
                }
                pid = Qdrant.upsert_point(rec.qdrant_point_id, vec, payload)
                rec.write({
                    "qdrant_point_id": pid,
                    "state": "indexed",
                    "error_message": False,
                })
            except Exception as exc:
                _logger.exception("ai.skill#%s tokenize failed", rec.id)
                rec.write({"state": "error", "error_message": str(exc)[:2000]})
        return True

    def action_purge_from_qdrant(self):
        Qdrant = self.env["ai.qdrant.skills.client"]
        for rec in self:
            if rec.qdrant_point_id:
                try:
                    Qdrant.delete_point(rec.qdrant_point_id)
                except Exception:
                    _logger.exception("ai.skill#%s purge failed", rec.id)
            rec.write({"qdrant_point_id": False, "state": "draft"})

    def action_view_steps(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Pipeline Steps"),
            "res_model": "ai.pipeline.step",
            "view_mode": "list,form",
            "domain": [("skill_id", "=", self.id)],
            "context": {"default_skill_id": self.id},
        }

    # ── Matching (runtime) ─────────────────────────────────────
    @api.model
    def match_for_vector(self, vector, limit=5, score_threshold=0.65, lang=None):
        """Return a recordset of top-K skills matching ``vector``.

        Caller passes the *document* embedding; we search the skills
        collection and reconstruct the recordset in Qdrant score order.

        :param vector: list[float] — document embedding.
        :param limit: int — max skills to return.
        :param score_threshold: float — Qdrant cutoff (0..1).
        :param lang: optional Odoo language code to filter by
            (skills with language='all' always pass).
        :return: (recordset, scores) — parallel lists aligned on order.
        """
        Qdrant = self.env["ai.qdrant.skills.client"]
        hits = Qdrant.search(
            vector=vector, limit=limit, score_threshold=score_threshold,
        )
        if not hits:
            return self.browse(), []
        ordered_ids = [int(h["payload"]["res_id"]) for h in hits
                       if (h.get("payload") or {}).get("res_id")]
        scores = [float(h.get("score") or 0.0) for h in hits]
        recs = self.browse(ordered_ids).exists()
        if lang:
            recs = recs.filtered(lambda s: s.language in ("all", lang))
        # Preserve Qdrant score order on the filtered recordset.
        score_by_id = dict(zip(ordered_ids, scores))
        sorted_recs = recs.sorted(key=lambda r: -score_by_id.get(r.id, 0.0))
        sorted_scores = [score_by_id.get(r.id, 0.0) for r in sorted_recs]
        return sorted_recs, sorted_scores

    # ── Lifecycle hooks ────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        # Stamp module provenance from the XML id if available.
        for rec in recs:
            xmlid = rec.get_external_id().get(rec.id)
            if xmlid and not rec.module:
                rec.module = xmlid.split(".", 1)[0]
        return recs

    def write(self, vals):
        res = super().write(vals)
        # Re-index if description changed.
        if "description" in vals:
            self.filtered(lambda r: r.state == "indexed").write({"state": "stale"})
        return res
