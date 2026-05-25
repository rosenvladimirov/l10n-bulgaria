# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Каталог на отпадъчните кодове по Приложение 1 на Наредба №2/2014.

Шестцифрена йерархия (раздел → подраздел → код), огледални неопасни/опасни
двойки по чл. 10. Кодовете със звезда (*) са опасни.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WasteCode(models.Model):
    _name = "l10n.bg.waste.code"
    _description = "Bulgarian Waste Code (Ordinance 2/2014, Annex 1)"
    _order = "code"
    _rec_name = "display_name"

    code = fields.Char(
        string="Code",
        size=8,
        required=True,
        index=True,
        help="6-digit code in the official 'XX XX XX' format (with spaces). "
             "Hazardous codes carry the suffix '*'.",
    )
    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
        index=True,
    )
    parent_id = fields.Many2one(
        "l10n.bg.waste.code",
        string="Section",
        ondelete="restrict",
        help="Parent section (e.g. '15 01' is the parent of '15 01 02'; "
             "'15' is the top-level chapter).",
    )
    child_ids = fields.One2many(
        "l10n.bg.waste.code",
        "parent_id",
        string="Children",
    )
    level = fields.Selection(
        [
            ("chapter", "Chapter (2-digit)"),
            ("subchapter", "Subchapter (4-digit)"),
            ("code", "Code (6-digit)"),
        ],
        compute="_compute_level",
        store=True,
        index=True,
    )
    is_hazardous = fields.Boolean(
        string="Hazardous",
        help="Codes marked with '*' in the regulation are hazardous waste "
             "and trigger stricter handling and reporting requirements "
             "(ID document per Annex 8, dedicated permit, etc.).",
    )
    is_mirror = fields.Boolean(
        string="Mirror Code",
        help="Has a paired hazardous/non-hazardous counterpart per "
             "Art. 10 of Ordinance 2/2014. Classification of a mirror "
             "code requires lab testing (working sheets - Annexes 5/6).",
    )
    mirror_code_id = fields.Many2one(
        "l10n.bg.waste.code",
        string="Mirror Counterpart",
    )
    default_uom_id = fields.Many2one(
        "uom.uom",
        string="Default UoM",
        default=lambda self: self.env.ref("uom.product_uom_kgm", raise_if_not_found=False),
        help="Default unit of measure for accounting waste quantities. "
             "Regulatory reports (Annex 4/18) always use kilograms or tons.",
    )
    description = fields.Text(
        string="Notes",
        translate=True,
    )
    active = fields.Boolean(default=True)

    # --- Constraints (Odoo 19 modern API; _sql_constraints е deprecated)
    # NB: Constraint attribute names MUST start with '_' (Odoo 19 ORM assert). ---
    _code_unique = models.Constraint(
        "unique(code)",
        "Waste code must be unique.",
    )

    # --- Computes -----------------------------------------------------------
    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.code} {rec.name}" if rec.code and rec.name else (rec.code or rec.name or "")
            )

    @api.depends("code")
    def _compute_level(self):
        # XX = chapter; XX XX = subchapter; XX XX XX = leaf code.
        for rec in self:
            digits = (rec.code or "").replace(" ", "").replace("*", "")
            if len(digits) == 2:
                rec.level = "chapter"
            elif len(digits) == 4:
                rec.level = "subchapter"
            elif len(digits) == 6:
                rec.level = "code"
            else:
                rec.level = False

    # --- Validation ---------------------------------------------------------
    @api.constrains("code")
    def _check_code_format(self):
        import re
        # Допустими формати: 'XX', 'XX XX', 'XX XX XX', с опционална '*' за опасни.
        pattern = re.compile(r"^\d{2}( \d{2}){0,2}\*?$")
        for rec in self:
            if rec.code and not pattern.match(rec.code):
                raise ValidationError(
                    _(
                        "Waste code %s has an invalid format. "
                        "Expected 'XX', 'XX XX' or 'XX XX XX', optionally followed by '*' for hazardous codes."
                    ) % rec.code
                )

    @api.constrains("mirror_code_id", "is_mirror")
    def _check_mirror_pair(self):
        for rec in self:
            if rec.mirror_code_id and rec.mirror_code_id == rec:
                raise ValidationError(_("A waste code cannot be its own mirror counterpart."))
            if rec.is_mirror and not rec.mirror_code_id:
                raise ValidationError(
                    _("Code %s is flagged as a mirror code but no counterpart is set.") % rec.code
                )
