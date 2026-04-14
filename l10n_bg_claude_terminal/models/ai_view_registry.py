# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiViewRegistry(models.Model):
    _name = "ai.view.registry"
    _description = "AI Tokenizer — View Registry"
    _order = "priority asc, id asc"

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_name = fields.Char(
        string="Technical Name",
        related="model_id.model",
        store=True,
        index=True,
    )
    view_type = fields.Selection(
        [("form", "Form"), ("list", "List"), ("kanban", "Kanban")],
        string="View Type",
        required=True,
        default="form",
    )
    view_id = fields.Many2one(
        "ir.ui.view",
        string="Specific View",
        domain="[('model', '=', model_name), ('type', '=', view_type)]",
        help="Leave empty to use the default view for this model/type.",
    )
    field_spec = fields.Text(
        string="Field Spec (JSON)",
        help="Cached parsed arch — list of field paths with types and depth.",
    )
    embedding_provider = fields.Selection(
        [
            ("user", "Use user settings"),
            ("ollama", "Ollama"),
            ("openai", "OpenAI"),
            ("voyage", "Voyage AI"),
            ("anthropic", "Anthropic"),
        ],
        string="Embedding Provider",
        default="user",
        help="Override the user's default embedding provider for this entry.",
    )
    active = fields.Boolean(default=True)
    last_parsed = fields.Datetime(
        string="Last Arch Parse",
        readonly=True,
    )
    priority = fields.Integer(
        default=10,
        help="Lower = higher priority. Tokenization cron processes low-priority first.",
    )
    document_count = fields.Integer(
        compute="_compute_document_count",
        string="Documents",
    )

    _sql_constraints = [
        (
            "uniq_model_view",
            "UNIQUE(model_id, view_type, view_id)",
            "Registry entry already exists for this model / view type / view.",
        ),
    ]

    @api.depends("model_id", "view_type", "view_id")
    def _compute_name(self):
        for rec in self:
            parts = [rec.model_id.model or "", rec.view_type or ""]
            if rec.view_id:
                parts.append(f"#{rec.view_id.id}")
            rec.name = " / ".join(p for p in parts if p)

    @api.depends("model_name", "view_type")
    def _compute_document_count(self):
        Doc = self.env["ai.composite.document"]
        for rec in self:
            rec.document_count = Doc.search_count([("registry_id", "=", rec.id)])

    @api.model
    def _is_enabled(self):
        """Feature gate — tokenization is disabled unless Qdrant is configured."""
        user = self.env.user
        return bool(user.claude_qdrant_url)

    def action_parse_arch(self):
        """Re-parse the view arch and refresh field_spec."""
        parser = self.env["ai.view.parser"]
        for rec in self:
            spec = parser.parse(rec.model_name, rec.view_type, rec.view_id.id or None)
            rec.field_spec = json.dumps(spec, ensure_ascii=False, indent=2)
            rec.last_parsed = fields.Datetime.now()
        return True

    def action_view_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Composite Documents — %s") % self.name,
            "res_model": "ai.composite.document",
            "view_mode": "list,form",
            "domain": [("registry_id", "=", self.id)],
            "context": {"default_registry_id": self.id},
        }

    # ──────────────────────────────────────────────────────────
    # Tokenization orchestration
    # ──────────────────────────────────────────────────────────

    def action_tokenize_all(self):
        """Build composite documents for *every* record of the model.

        Run manually from the form view; in production the cron does this.
        """
        Doc = self.env["ai.composite.document"]
        for rec in self:
            if not rec.active:
                continue
            source = self.env[rec.model_name].search([])
            for row in source:
                doc = Doc.search([
                    ("registry_id", "=", rec.id),
                    ("res_id", "=", row.id),
                ], limit=1)
                if not doc:
                    doc = Doc.create({
                        "registry_id": rec.id,
                        "res_id": row.id,
                        "company_id": (
                            row.company_id.id
                            if "company_id" in row._fields and row.company_id
                            else False
                        ),
                        "db_name": self.env.cr.dbname,
                    })
                doc.action_tokenize_and_index()
        return True

    @api.model
    def tokenize_record(self, model_name, res_id, view_type="form"):
        """RPC entrypoint — called from OWL 'Tokenize Now' button.

        Finds or creates the registry + composite document for the given
        (model, view_type), runs the synchronous build → embed → upsert cycle.
        """
        if not self._is_enabled():
            return {"ok": False, "error": "AI tokenization disabled — configure Qdrant first."}
        IrModel = self.env["ir.model"]
        model = IrModel._get(model_name)
        if not model:
            return {"ok": False, "error": f"Unknown model: {model_name}"}
        registry = self.search([
            ("model_id", "=", model.id),
            ("view_type", "=", view_type),
        ], limit=1)
        if not registry:
            registry = self.create({
                "model_id": model.id,
                "view_type": view_type,
            })
            registry.action_parse_arch()
        record = self.env[model_name].browse(res_id)
        if not record.exists():
            return {"ok": False, "error": f"Record {model_name}#{res_id} not found"}
        Doc = self.env["ai.composite.document"]
        doc = Doc.search([
            ("registry_id", "=", registry.id),
            ("res_id", "=", res_id),
        ], limit=1)
        if not doc:
            doc = Doc.create({
                "registry_id": registry.id,
                "res_id": res_id,
                "company_id": (
                    record.company_id.id
                    if "company_id" in record._fields and record.company_id
                    else False
                ),
                "db_name": self.env.cr.dbname,
            })
        result = doc.action_tokenize_and_index()
        return {
            "ok": result is True,
            "document_id": doc.id,
            "state": doc.state,
            "token_count": doc.token_count,
            "error": doc.error_message or None,
        }
