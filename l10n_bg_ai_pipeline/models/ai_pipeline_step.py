# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import ast
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

PIPELINE_SELECTION = [
    ("tokenize", "Tokenize"),
    ("post", "Post"),
    ("refresh", "Refresh"),
]


class AiPipelineStep(models.Model):
    """One executable step in a named pipeline.

    Steps are ordered by ``(sequence, id)`` within their pipeline and
    executed by ``ai.pipeline.runner``.  A step may be:

    * **Base** — always runs (``skill_id`` is empty).  Seeded via XML
      data by the platform or by glue modules.
    * **Skill-injected** — runs only when its ``skill_id`` is among the
      skills matched for the current document.  This is what we mean
      by "the skill itself says where it attaches".
    """

    _name = "ai.pipeline.step"
    _description = "AI Pipeline Step"
    _order = "pipeline, sequence, id"

    name = fields.Char(required=True)
    pipeline = fields.Selection(
        PIPELINE_SELECTION, required=True, default="tokenize", index=True,
    )
    sequence = fields.Integer(default=50, index=True)

    # Callable: env[model].<method>(ctx) → ctx
    model = fields.Char(required=True, help="Odoo model holding the callable.")
    method = fields.Char(required=True, help=(
        "Method on ``model``. Signature: (self, ctx: dict) -> dict. "
        "Must mutate or return the shared context."
    ))

    # Activation
    skill_id = fields.Many2one(
        "ai.skill",
        ondelete="cascade",
        help=(
            "When set, the step runs only for documents whose matched "
            "skills include this one — Anthropic-style injection."
        ),
    )
    trigger_domain = fields.Char(
        help=(
            "Python literal domain evaluated against the runtime context "
            "(e.g. `[('source_model','=','account.move')]`). Empty = "
            "always passes."
        ),
    )
    on_error = fields.Selection([
        ("abort", "Abort pipeline"),
        ("skip", "Skip and continue"),
        ("retry", "Retry once"),
    ], default="skip", required=True)

    # Provenance
    module = fields.Char(help="Source module — set automatically from XML id.")
    active = fields.Boolean(default=True)

    # Runtime stats (last execution)
    last_run_state = fields.Selection([
        ("ok", "OK"),
        ("skipped", "Skipped"),
        ("error", "Error"),
    ], readonly=True)
    last_run_message = fields.Text(readonly=True)
    last_run_date = fields.Datetime(readonly=True)

    _sql_constraints = [
        ("ai_pipeline_step_name_uniq",
         "unique(pipeline, name)",
         "Step name must be unique per pipeline."),
    ]

    # ──────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────
    @api.constrains("trigger_domain")
    def _check_trigger_domain(self):
        for rec in self:
            if not rec.trigger_domain:
                continue
            try:
                parsed = ast.literal_eval(rec.trigger_domain)
            except (ValueError, SyntaxError) as exc:
                raise ValidationError(_(
                    "Step %s: trigger_domain is not a valid Python "
                    "literal: %s"
                ) % (rec.name, exc)) from None
            if not isinstance(parsed, (list, tuple)):
                raise ValidationError(_(
                    "Step %s: trigger_domain must be a list of tuples."
                ) % rec.name)

    # Note: callable validity is checked lazily in ``_invoke`` so that
    # data-seeded steps in a module that depends on another module do
    # not fail the install order.  The step just logs a warning and is
    # treated as ``skipped`` at runtime.

    # ──────────────────────────────────────────────────────────
    # Runtime helpers
    # ──────────────────────────────────────────────────────────
    def _matches(self, ctx):
        """Return True if this step should run for the given context.

        Skill-gated steps need their ``skill_id`` to be present in
        ``ctx['matched_skill_ids']``.  Trigger domain is evaluated
        against ``ctx`` as a flat dict (no ORM semantics — just
        field→value comparison on the context payload).
        """
        self.ensure_one()
        if self.skill_id:
            matched = ctx.get("matched_skill_ids") or []
            if self.skill_id.id not in matched:
                return False
        if self.trigger_domain:
            # trigger_domain is validated at write-time by
            # _check_trigger_domain, so parsing here cannot fail for a
            # stored record.
            domain = ast.literal_eval(self.trigger_domain)
            return self._eval_flat_domain(domain, ctx)
        return True

    @staticmethod
    def _eval_flat_domain(domain, ctx):
        """Tiny domain evaluator for flat dict contexts.

        Supports the basic operators (=, !=, in, not in); does not
        support '|' / '&' prefix notation — keep domains simple.
        """
        for leaf in domain:
            if not isinstance(leaf, (list, tuple)) or len(leaf) != 3:
                continue
            field, op, value = leaf
            left = ctx.get(field)
            if op == "=":
                if left != value:
                    return False
            elif op == "!=":
                if left == value:
                    return False
            elif op == "in":
                if left not in (value or []):
                    return False
            elif op == "not in":
                if left in (value or []):
                    return False
            else:
                # Unknown operator → treat as non-match, don't surprise.
                return False
        return True

    def _invoke(self, ctx):
        """Call the configured method with ``ctx`` and return the new ctx.

        Missing model/method degrades to a ``skipped`` outcome with a
        warning in the log — we never want a half-installed module to
        hard-crash the tokenize pipeline.
        """
        self.ensure_one()
        Model = self.env.get(self.model)
        if Model is None:
            _logger.warning(
                "pipeline step %s: model %s is not installed, skipping",
                self.name, self.model,
            )
            return ctx
        fn = getattr(Model, self.method, None)
        if fn is None:
            _logger.warning(
                "pipeline step %s: %s has no method %s, skipping",
                self.name, self.model, self.method,
            )
            return ctx
        # Deliberately pass a raw dict, not a kwargs expansion, so
        # steps can mutate shared state across the pipeline.
        result = fn(ctx)
        return result if isinstance(result, dict) else ctx

    # ──────────────────────────────────────────────────────────
    # Create — stamp module provenance
    # ──────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            xmlid = rec.get_external_id().get(rec.id)
            if xmlid and not rec.module:
                rec.module = xmlid.split(".", 1)[0]
        return recs
