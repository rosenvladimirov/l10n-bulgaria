# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""ai.model — регистър на наличните AI (Claude) модели.

Прост code+name справочник, за да може настройките (напр. кой модел да
ползва осчетоводяването на фактури) да сочат към избираем запис, а не към
свободен текст. `code` = Anthropic API идентификаторът (claude-sonnet-4-6),
`name` = човешко име. Seed-нат с текущите модели; добавяй нови без код.
"""
from odoo import fields, models


class AiModel(models.Model):
    _name = "ai.model"
    _description = "AI Model (Anthropic/Claude registry)"
    _order = "sequence, name"

    name = fields.Char(
        required=True, translate=True,
        help="Human-readable name, e.g. 'Claude Sonnet 4.6'.")
    code = fields.Char(
        required=True, index=True,
        help="Anthropic API model identifier, e.g. 'claude-sonnet-4-6'.")
    tier = fields.Selection(
        [("opus", "Opus (max capability)"),
         ("sonnet", "Sonnet (balanced)"),
         ("haiku", "Haiku (fast/cheap)"),
         ("other", "Other")],
        default="other",
        help="Capability/cost tier — informational, for picking sensibly.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Char(help="Optional note (context window, pricing hint, ...).")

    _sql_constraints = [
        ("uniq_code", "unique(code)", "This model code already exists."),
    ]

    def name_get(self):
        return [(rec.id, "%s (%s)" % (rec.name, rec.code)) for rec in self]
