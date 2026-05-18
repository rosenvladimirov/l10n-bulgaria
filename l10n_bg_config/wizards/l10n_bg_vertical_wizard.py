# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Визард на една инсталационна секция (вертикал).

Отваря се от бутона в res.config.settings за съответната секция.
Показва подредените стъпки; всеки ред има действия Install / Open
config / Mark done. Самата gating логика е в `l10n.bg.vertical`.
"""

from odoo import fields, models


class L10nBgVerticalWizard(models.TransientModel):
    _name = "l10n.bg.vertical.wizard"
    _description = "Bulgarian Localization Vertical Installer Wizard"

    vertical_id = fields.Many2one(
        "l10n.bg.vertical", required=True, readonly=True, ondelete="cascade"
    )
    code = fields.Char(related="vertical_id.code", readonly=True)
    name = fields.Char(related="vertical_id.name", readonly=True)
    edition = fields.Selection(
        related="vertical_id.edition", readonly=True
    )
    description = fields.Text(
        related="vertical_id.description", readonly=True
    )
    state = fields.Selection(related="vertical_id.state", readonly=True)
    progress = fields.Float(
        related="vertical_id.progress", readonly=True
    )
    step_ids = fields.Many2many(
        "l10n.bg.vertical.step",
        compute="_compute_step_ids",
        string="Steps",
    )

    def _compute_step_ids(self):
        for wiz in self:
            wiz.step_ids = wiz.vertical_id.step_ids

    def action_refresh(self):
        """Презарежда визарда (след install/config действие)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "%s — %s" % (self.code, self.name),
            "res_model": "l10n.bg.vertical.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
