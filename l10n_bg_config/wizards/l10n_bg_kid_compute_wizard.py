# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, fields, models


class L10nBgKidComputeWizard(models.TransientModel):
    _name = "l10n.bg.kid.compute.wizard"
    _description = "Derive primary economic activity (КИД)"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    primary_kid_id = fields.Many2one(
        "l10n.bg.kid", string="Derived primary КИД", readonly=True
    )
    result_line_ids = fields.One2many(
        "l10n.bg.kid.compute.wizard.line",
        "wizard_id",
        string="Ranking",
        readonly=True,
    )

    def action_compute(self):
        self.ensure_one()
        ranking = self.company_id._l10n_bg_compute_primary_kid(
            self.date_from, self.date_to
        )
        lines = [
            Command.create(
                {
                    "kid_id": kid.id,
                    "net_revenue": revenue,
                    "is_primary": idx == 0,
                }
            )
            for idx, (kid, revenue) in enumerate(ranking)
        ]
        self.write(
            {
                "result_line_ids": [Command.clear()] + lines,
                "primary_kid_id": self.company_id.l10n_bg_primary_kid_id.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "l10n.bg.kid.compute.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class L10nBgKidComputeWizardLine(models.TransientModel):
    _name = "l10n.bg.kid.compute.wizard.line"
    _description = "Primary КИД derivation result line"
    _order = "net_revenue desc"

    wizard_id = fields.Many2one("l10n.bg.kid.compute.wizard", ondelete="cascade")
    kid_id = fields.Many2one("l10n.bg.kid", string="Economic activity", readonly=True)
    net_revenue = fields.Monetary(
        string="Net sales revenue",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="wizard_id.company_id.currency_id", readonly=True
    )
    is_primary = fields.Boolean(string="Primary", readonly=True)
