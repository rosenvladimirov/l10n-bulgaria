# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import time

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AiPipelineRunner(models.AbstractModel):
    """Executes named pipelines step by step.

    The runner is what implements "the skill says where it attaches":
    base steps are loaded first, a dedicated ``skill_resolution`` step
    discovers relevant skills for the document, and any skill-gated
    steps then become eligible for the remainder of the run.

    All step I/O flows through a single ``ctx`` dict passed by
    reference — the convention is:

        ctx = {
            "doc": ai.composite.document recordset,
            "source_model": str,
            "source_res_id": int,
            "matched_skill_ids": list[int],   # filled by skill_resolution
            "matched_skill_scores": dict[int, float],
            "result": dict,                    # arbitrary accumulator
            "abort": bool,                     # hard stop flag
            # steps may add their own keys freely
        }
    """

    _name = "ai.pipeline.runner"
    _description = "AI Pipeline Runner"

    # ──────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────
    @api.model
    def run(self, pipeline, doc=None, extra_ctx=None):
        """Execute ``pipeline`` against ``doc`` (ai.composite.document).

        Returns the final ctx dict.  Creates an ai.pipeline.run audit
        record along the way.
        """
        if not pipeline:
            raise ValueError("pipeline name is required")
        ctx = self._init_context(doc, extra_ctx)
        run_rec = self._open_run(pipeline, ctx)
        started = time.monotonic()
        executed = 0
        log_lines = []
        error_step = None
        error_msg = None
        final_state = "done"

        try:
            # Load base + skill-gated steps up front.  Skill-gated steps
            # stay inert until ``matched_skill_ids`` is populated — that
            # is typically done by a step named 'skill_resolution'.
            steps = self._load_steps(pipeline)
            i = 0
            while i < len(steps):
                step = steps[i]
                i += 1
                if not step._matches(ctx):
                    log_lines.append(f"[skip] {step.name}")
                    step.write({
                        "last_run_state": "skipped",
                        "last_run_message": "matches=False",
                        "last_run_date": fields.Datetime.now(),
                    })
                    continue

                try:
                    ctx = step._invoke(ctx) or ctx
                    executed += 1
                    log_lines.append(f"[ok]   {step.name}")
                    step.write({
                        "last_run_state": "ok",
                        "last_run_message": False,
                        "last_run_date": fields.Datetime.now(),
                    })
                except Exception as exc:
                    _logger.exception(
                        "pipeline=%s step=%s failed", pipeline, step.name,
                    )
                    step.write({
                        "last_run_state": "error",
                        "last_run_message": str(exc)[:2000],
                        "last_run_date": fields.Datetime.now(),
                    })
                    log_lines.append(f"[err]  {step.name}: {exc}")

                    if step.on_error == "retry":
                        try:
                            ctx = step._invoke(ctx) or ctx
                            executed += 1
                            log_lines.append(f"[retry-ok] {step.name}")
                            continue
                        except Exception as exc2:
                            log_lines.append(
                                f"[retry-err] {step.name}: {exc2}"
                            )
                            exc = exc2

                    if step.on_error == "abort":
                        error_step = step
                        error_msg = str(exc)
                        final_state = "error"
                        break
                    # else: skip → continue to next step

                if ctx.get("abort"):
                    log_lines.append(f"[abort] requested after {step.name}")
                    final_state = "aborted"
                    break

        finally:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            run_rec.write({
                "finished": fields.Datetime.now(),
                "duration_ms": elapsed_ms,
                "state": final_state,
                "matched_skill_ids": [(6, 0, ctx.get("matched_skill_ids") or [])],
                "executed_step_count": executed,
                "error_step_id": error_step.id if error_step else False,
                "error_message": error_msg or False,
                "log": "\n".join(log_lines),
            })
        return ctx

    # ──────────────────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────────────────
    def _init_context(self, doc, extra_ctx):
        ctx = {
            "doc": doc,
            "source_model": doc.model_name if doc else None,
            "source_res_id": doc.res_id if doc else None,
            "matched_skill_ids": [],
            "matched_skill_scores": {},
            "result": {},
            "abort": False,
        }
        if extra_ctx:
            ctx.update(extra_ctx)
        return ctx

    def _open_run(self, pipeline, ctx):
        doc = ctx.get("doc")
        return self.env["ai.pipeline.run"].create({
            "pipeline": pipeline,
            "composite_document_id": doc.id if doc else False,
            "source_model": ctx.get("source_model") or False,
            "source_res_id": ctx.get("source_res_id") or 0,
        })

    def _load_steps(self, pipeline):
        return self.env["ai.pipeline.step"].search([
            ("pipeline", "=", pipeline),
            ("active", "=", True),
        ])

    # ──────────────────────────────────────────────────────────
    # Built-in step handlers
    #
    # These implement the base tokenize pipeline.  They live on the
    # runner itself so that the data XML only references one model,
    # keeping the seed file short.  Glue modules are free to add
    # their own model + method pairs.
    # ──────────────────────────────────────────────────────────
    @api.model
    def step_build_text(self, ctx):
        """Flatten the source record into a structured text blob."""
        doc = ctx["doc"]
        doc.ensure_one()
        Builder = self.env["ai.document.builder"]
        registry = doc.registry_id
        record = self.env[doc.model_name].browse(doc.res_id)
        if not record.exists():
            ctx["abort"] = True
            ctx["abort_reason"] = "source_record_missing"
            return ctx
        text, token_count = Builder.build(registry, record)
        ctx["text"] = text
        ctx["token_count"] = token_count
        ctx["record"] = record
        return ctx

    @api.model
    def step_embed(self, ctx):
        """Embed the text produced by ``step_build_text``."""
        Embed = self.env["ai.embedding.provider"]
        text = ctx.get("text")
        if not text:
            raise ValueError("step_embed: ctx['text'] is empty")
        vectors = Embed.embed([text])
        if not vectors:
            raise ValueError("step_embed: provider returned no vectors")
        ctx["vector"] = vectors[0]
        return ctx

    @api.model
    def step_upsert_qdrant(self, ctx):
        """Upsert the composite document vector into Qdrant."""
        Qdrant = self.env["ai.qdrant.client"]
        doc = ctx["doc"]
        record = ctx.get("record") or self.env[doc.model_name].browse(doc.res_id)
        vector = ctx["vector"]
        Qdrant.ensure_collection(len(vector))
        payload = {
            "model": doc.model_name,
            "res_id": doc.res_id,
            "view_type": doc.view_type,
            "company_id": doc.company_id.id or 0,
            "db_name": doc.db_name or self.env.cr.dbname,
            "display_name": record.display_name,
            "document_text": ctx.get("text"),
            "token_count": ctx.get("token_count") or 0,
            "write_date": (
                record.write_date.isoformat() if record.write_date else None
            ),
        }
        pid = Qdrant.upsert_point(doc.qdrant_point_id, vector, payload)
        doc.write({
            "document_text": ctx.get("text"),
            "token_count": ctx.get("token_count") or 0,
            "qdrant_point_id": pid,
            "source_write_date": record.write_date or False,
            "state": "indexed",
            "error_message": False,
        })
        ctx["qdrant_point_id"] = pid
        return ctx

    @api.model
    def step_skill_resolution(self, ctx):
        """Populate ``matched_skill_ids`` via Qdrant skill search.

        After this step finishes, skill-gated pipeline steps whose
        ``skill_id`` is in ``matched_skill_ids`` become eligible.
        Steps added *earlier* in sequence are unaffected — which is
        why this step is typically sequenced before any skill-gated
        injections (default 90).
        """
        Skill = self.env["ai.skill"]
        vector = ctx.get("vector")
        if not vector:
            ctx["matched_skill_ids"] = []
            return ctx
        lang = self.env.lang or "en_US"
        recs, scores = Skill.match_for_vector(
            vector=vector, limit=10, score_threshold=0.65, lang=lang,
        )
        ctx["matched_skill_ids"] = recs.ids
        ctx["matched_skill_scores"] = dict(zip(recs.ids, scores))
        _logger.info(
            "skill_resolution: matched %s skills for %s#%s",
            len(recs), ctx.get("source_model"), ctx.get("source_res_id"),
        )
        return ctx
