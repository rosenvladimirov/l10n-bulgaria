# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Блокът е материализиран нарочно: между парсването и публикуването стои
екран, на който се вижда какво е разпознато и към кой снипет отива. Ако
мапването се провери само в изхода, грешката се намира чак в статията.
"""

import json

from odoo import api, fields, models

from .claude_snippet_rule import BLOCK_KINDS


class ClaudeArtifactBlock(models.Model):
    _name = "claude.artifact.block"
    _description = "Claude Artifact Block"
    _order = "artifact_id, sequence, id"

    artifact_id = fields.Many2one(
        "claude.artifact", required=True, ondelete="cascade", index=True,
    )
    sequence = fields.Integer(default=10, index=True)
    kind = fields.Selection(BLOCK_KINDS, required=True, index=True)
    level = fields.Integer(help="Heading level, 1 to 6.")
    anchor = fields.Char()
    lang = fields.Char("Code Language")
    body_html = fields.Text("Block HTML")
    text = fields.Text()
    meta_json = fields.Text("Metadata (JSON)")
    rule_id = fields.Many2one(
        "claude.snippet.rule", compute="_compute_rule_id", store=True, readonly=True,
    )
    snippet_key = fields.Char(related="rule_id.snippet_key", store=True, readonly=True)
    excluded = fields.Boolean(
        help="Excluded blocks are skipped when the blog post is built.",
    )

    @api.depends("kind", "level")
    def _compute_rule_id(self):
        rules = self.env["claude.snippet.rule"]
        for block in self:
            block.rule_id = rules._rule_for(block)

    @property
    def meta(self):
        try:
            return json.loads(self.meta_json or "{}")
        except ValueError:
            return {}

    @api.model
    def _vals_from_parsed(self, block):
        return {
            "sequence": block["sequence"],
            "kind": block["kind"],
            "level": block["level"],
            "anchor": block["anchor"],
            "lang": block["lang"],
            "body_html": block["html"],
            "text": block["text"],
            "meta_json": json.dumps(block["meta"], ensure_ascii=False),
        }
