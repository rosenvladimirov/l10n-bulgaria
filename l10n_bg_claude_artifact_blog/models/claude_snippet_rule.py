# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Правилата, които решават кой блок към кой Odoo снипет отива.

Мапването живее в данни, не в код — снипетите на Odoo се сменят между
сериите, а правилото „таблица -> s_text_block с table-responsive" не е
алгоритъм, а решение. Сменя се от екрана, без миграция.
"""

from odoo import api, fields, models

BLOCK_KINDS = [
    ("kicker", "Kicker (overline)"),
    ("standfirst", "Standfirst (lead paragraph)"),
    ("heading", "Heading"),
    ("paragraph", "Paragraph"),
    ("list", "List"),
    ("definitions", "Definition list"),
    ("kpi", "Single figure"),
    ("kpi_group", "Figures board"),
    ("code", "Code"),
    ("table", "Table"),
    ("callout", "Callout / alert"),
    ("quote", "Quote"),
    ("svg", "Inline SVG"),
    ("image", "Image"),
    ("caption", "Caption"),
    ("accordion", "Accordion"),
    ("separator", "Separator"),
]


class ClaudeSnippetRule(models.Model):
    _name = "claude.snippet.rule"
    _description = "Claude Artifact to Odoo Snippet Rule"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    block_kind = fields.Selection(BLOCK_KINDS, required=True, index=True)
    # Празно = важи за всяко ниво; иначе точното ниво на заглавието
    heading_level = fields.Integer(
        help="Applies only to headings of this level. Leave 0 for any level.",
    )
    snippet_key = fields.Char(
        required=True,
        help="Technical name of the target Odoo snippet, e.g. s_text_block.",
    )
    template_key = fields.Char(
        required=True,
        help="QWeb template rendering this block, e.g. "
             "l10n_bg_claude_artifact_blog.snippet_text_block.",
    )
    standalone = fields.Boolean(
        default=True,
        help="A standalone block becomes its own <section>. A non-standalone one "
             "is merged into the surrounding text section, the way headings of "
             "level 3 and paragraphs belong together.",
    )
    starts_section = fields.Boolean(
        help="This block opens a new section — used by level 2 headings, which "
             "also become the anchors of the table of content.",
    )
    note = fields.Text()

    @api.model
    def _rule_for(self, block):
        """Правилото за конкретен блок: по-точното (с ниво) бие общото."""
        kind = block.get("kind") if isinstance(block, dict) else block.kind
        level = (block.get("level") if isinstance(block, dict) else block.level) or 0
        rules = self.search([("block_kind", "=", kind)])
        exact = rules.filtered(lambda rule: rule.heading_level == level)
        return (exact or rules.filtered(lambda rule: not rule.heading_level))[:1]
