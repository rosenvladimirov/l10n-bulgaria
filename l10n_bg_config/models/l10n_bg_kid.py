# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class L10nBgKid(models.Model):
    """Bulgarian Classification of Economic Activities (КИД / NKID).

    Canonical, versioned, hierarchical reference table living in the
    localization *foundation* module so that every domain can share a
    single КИД definition:

        section (1 letter) -> division (2 digits)
                           -> group    (3 digits, XX.X)
                           -> class    (4 digits, XX.XX)

    КИД-2008 is aligned 1:1 with NACE Rev.2 (ISIC Rev.4); КИД-2025 with
    NACE Rev.2.1 (ISIC Rev.5). Both editions can coexist via
    ``kid_version`` (the sector letters shift between them — in КИД-2025
    the old sector ``J`` is split into ``J`` + ``K`` and every following
    letter moves by +1, ending at ``V``).

    This model is intentionally *thin and neutral*: domain modules extend
    it through prototype inheritance (``_name = '...'; _inherit =
    ['l10n.bg.kid']``) and add their own fields without touching this
    definition (e.g. ``bg.hr.payroll.economic.activity`` adds the MOD
    minimum-insurance-income amounts). The ``level`` keys are kept as
    ``section/division/group/class`` to stay byte-compatible with the
    pre-existing payroll seed and views — do not rename them.
    """

    _name = "l10n.bg.kid"
    _description = "Bulgarian Classification of Economic Activities (КИД)"
    _order = "code"
    _rec_name = "display_name"
    # Търсене по КОД и по име. _rec_name е computed display_name (non-stored),
    # затова стандартният name_search гърми при търсене по него — _rec_names_search
    # пренасочва search-а към реалните колони code+name (ползвачите пишат кода).
    _rec_names_search = ["code", "name"]

    name = fields.Char(string="Activity name", required=True, translate=True)
    code = fields.Char(string="КИД code", required=True, index=True)
    level = fields.Selection(
        selection=[
            ("section", "Section"),
            ("division", "Division"),
            ("group", "Group"),
            ("class", "Class"),
        ],
        string="Level",
        required=True,
        default="section",
        index=True,
    )
    kid_version = fields.Selection(
        selection=[("2008", "КИД-2008"), ("2025", "КИД-2025")],
        string="КИД edition",
        required=True,
        default="2025",
        index=True,
        help="КИД-2008 (NACE Rev.2) is in force for periods up to 2024; "
        "КИД-2025 (NACE Rev.2.1) applies from 01.01.2025.",
    )
    parent_id = fields.Many2one(
        "l10n.bg.kid", string="Parent activity", index=True, ondelete="cascade"
    )
    child_ids = fields.One2many(
        "l10n.bg.kid", "parent_id", string="Child activities"
    )
    partner_industry_id = fields.Many2one(
        "res.partner.industry",
        string="Odoo industry",
        help="Bridge to the standard Odoo industry "
        "(res.partner.industry / partner.industry_id). Set on sections.",
    )
    active = fields.Boolean(string="Active", default=True)

    # Accounting bridge — O2M / M2M / non-stored compute only, so
    # prototype-inheriting tables (payroll) gain NO extra DB column
    # (M2M lives in its own relation table, not on l10n_bg_kid).
    map_ids = fields.One2many(
        "l10n.bg.account.industry.map", "kid_id", string="Account mappings"
    )
    map_count = fields.Integer(compute="_compute_map_count")
    # Explicit many2many: one chart, many КИД. A sector-specific account
    # rule is shared by every КИД sector that needs it.
    account_rule_ids = fields.Many2many(
        "l10n.bg.account.kid.rule",
        relation="l10n_bg_kid_account_rule_rel",
        column1="kid_id",
        column2="rule_id",
        string="Account rules",
        help="Sector-specific account-code rules tied to this КИД sector.",
    )
    account_rule_count = fields.Integer(compute="_compute_account_rule_count")

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"

    def _compute_map_count(self):
        data = self.env["l10n.bg.account.industry.map"]._read_group(
            [("kid_id", "in", self.ids)], ["kid_id"], ["__count"]
        )
        counts = {kid.id: count for kid, count in data}
        for record in self:
            record.map_count = counts.get(record.id, 0)

    @api.depends("account_rule_ids")
    def _compute_account_rule_count(self):
        for record in self:
            record.account_rule_count = len(record.account_rule_ids)

    def action_view_maps(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "l10n.bg.account.industry.map",
            "view_mode": "list,form",
            "domain": [("kid_id", "=", self.id)],
            "context": {"default_kid_id": self.id},
        }

    @api.constrains("code", "kid_version")
    def _check_unique_code(self):
        """Python (not SQL) uniqueness — keeps prototype-inheriting tables
        (payroll) free of a DB-level constraint added during upgrade."""
        for record in self:
            dup = self.search_count(
                [
                    ("code", "=", record.code),
                    ("kid_version", "=", record.kid_version),
                    ("id", "!=", record.id),
                ]
            )
            if dup:
                raise ValidationError(
                    f"КИД code '{record.code}' already exists for edition "
                    f"{record.kid_version}!"
                )
