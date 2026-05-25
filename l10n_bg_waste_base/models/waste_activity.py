# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""R/D дейности по Приложения 1 и 2 на Допълнителните разпоредби на ЗУО.

R1–R13 — оползотворяване (recovery); D1–D15 — обезвреждане (disposal).
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WasteActivity(models.Model):
    _name = "l10n.bg.waste.activity"
    _description = "Waste Treatment Activity (R/D Codes)"
    _order = "type, sequence, code"
    _rec_name = "display_name"

    code = fields.Char(
        string="Code",
        size=4,
        required=True,
        index=True,
        help="R1..R13 (recovery) or D1..D15 (disposal).",
    )
    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )
    type = fields.Selection(
        [
            ("R", "Recovery"),
            ("D", "Disposal"),
        ],
        required=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        "unique(code)",
        "Activity code must be unique.",
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.code} — {rec.name}" if rec.code and rec.name else (rec.code or rec.name or "")
            )

    @api.constrains("code", "type")
    def _check_code_type_consistency(self):
        # R-кодовете трябва да са type='R', D-кодовете type='D'.
        for rec in self:
            if not rec.code or not rec.type:
                continue
            prefix = rec.code[0].upper()
            if prefix != rec.type:
                raise ValidationError(
                    _("Activity code %s does not match the selected type %s.") % (rec.code, rec.type)
                )
