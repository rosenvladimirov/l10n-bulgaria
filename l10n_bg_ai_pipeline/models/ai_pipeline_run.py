# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AiPipelineRun(models.Model):
    """Audit trail for one execution of a named pipeline.

    Created by ``ai.pipeline.runner.run`` at the start of a run and
    finalised at the end.  Serves as debug surface and as future
    input for learning (which skills fired, which steps failed).
    """

    _name = "ai.pipeline.run"
    _description = "AI Pipeline Run"
    _order = "create_date desc"
    _rec_name = "display_name"

    display_name = fields.Char(compute="_compute_display_name", store=True)
    pipeline = fields.Char(required=True, index=True)
    composite_document_id = fields.Many2one(
        "ai.composite.document", ondelete="cascade", index=True,
    )
    source_model = fields.Char(index=True)
    source_res_id = fields.Integer(index=True)

    started = fields.Datetime(default=fields.Datetime.now)
    finished = fields.Datetime()
    duration_ms = fields.Integer()

    state = fields.Selection([
        ("running", "Running"),
        ("done", "Done"),
        ("error", "Error"),
        ("aborted", "Aborted"),
    ], default="running", index=True)

    matched_skill_ids = fields.Many2many(
        "ai.skill",
        relation="ai_pipeline_run_skill_rel",
        column1="run_id",
        column2="skill_id",
    )
    executed_step_count = fields.Integer()
    error_step_id = fields.Many2one("ai.pipeline.step")
    error_message = fields.Text()

    log = fields.Text(help="Step-by-step trace: one line per step.")

    @api.depends("pipeline", "source_model", "source_res_id", "create_date")
    def _compute_display_name(self):
        for rec in self:
            src = f"{rec.source_model}#{rec.source_res_id}" if rec.source_model else "?"
            rec.display_name = f"[{rec.pipeline}] {src} @ {rec.create_date or ''}"
