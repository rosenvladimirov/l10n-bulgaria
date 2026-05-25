# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Wizard за въвеждане на отпадъчни кодове + decision при превишена квота."""
import ast

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WasteCodeWizard(models.TransientModel):
    _name = "l10n.bg.waste.code.wizard"
    _description = "Waste Code Entry Wizard"

    picking_id = fields.Many2one(
        "stock.picking",
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        "l10n.bg.waste.code.wizard.line",
        "wizard_id",
        string="Lines",
    )
    quota_breach_json = fields.Char(
        string="Quota Breach (internal)",
        readonly=True,
        help="Internal payload populated by stock.picking. JSON-like list "
             "of breach dicts produced by _l10n_bg_waste_check_quota.",
    )
    quota_warning = fields.Html(
        string="Quota Warning",
        compute="_compute_quota_warning",
    )
    has_block = fields.Boolean(compute="_compute_quota_warning")
    decision = fields.Selection(
        [
            ("proceed", "Proceed with shipment acceptance"),
            ("cancel", "Cancel acceptance"),
        ],
        string="Decision",
    )
    decision_note = fields.Text(
        string="Justification",
        help="Required when accepting a shipment that breaches the quota.",
    )

    @api.depends("quota_breach_json")
    def _compute_quota_warning(self):
        for wiz in self:
            breaches = wiz._parse_breach_json()
            wiz.has_block = any(b.get("is_block") for b in breaches)
            wiz.quota_warning = wiz._render_quota_warning(breaches)

    def _parse_breach_json(self):
        if not self.quota_breach_json:
            return []
        try:
            data = ast.literal_eval(self.quota_breach_json)
            if isinstance(data, list):
                return data
        except (ValueError, SyntaxError):
            return []
        return []

    def _render_quota_warning(self, breaches):
        if not breaches:
            return ""
        lines = []
        for b in breaches:
            code = self.env["l10n.bg.waste.code"].browse(b.get("waste_code_id"))
            severity = "danger" if b.get("is_block") else "warning"
            icon = "⛔" if b.get("is_block") else "⚠"
            lines.append(
                f"<div class='alert alert-{severity}'>"
                f"{icon} <b>{code.code}</b> — "
                f"YTD {b.get('ytd_kg', 0):.0f} kg + "
                f"incoming {b.get('incoming_kg', 0):.0f} kg = "
                f"<b>{b.get('future_used_kg', 0):.0f} / "
                f"{b.get('annual_quota_kg', 0):.0f} kg "
                f"({b.get('future_percent', 0):.1f}%)</b>"
                f"</div>"
            )
        return "".join(lines)

    # ------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        # 1) Прилага кодовете към move.line-овете.
        for line in self.line_ids:
            if line.move_line_id and line.waste_code_id:
                line.move_line_id.waste_code_id = line.waste_code_id

        # 2) Ако има блокиращ breach — изисквай decision + note.
        if self.has_block:
            if self.decision != "proceed":
                raise ValidationError(
                    _("This shipment would exceed the annual quota. "
                      "Choose 'Proceed' and provide a justification, "
                      "or 'Cancel' to abort acceptance.")
                )
            if not (self.decision_note or "").strip():
                raise ValidationError(
                    _("A justification note is required when accepting a shipment "
                      "that exceeds the annual quota.")
                )

        # 3) Запиши решението в chatter.
        breaches = self._parse_breach_json()
        decision_type = (
            "over_quota" if any(b.get("is_block") for b in breaches)
            else ("warning_80" if breaches else "normal")
        )
        self.picking_id._l10n_bg_waste_post_acceptance(
            decision=decision_type,
            note=self.decision_note,
        )

        # 4) Re-enter button_validate с флаг за пропускане на повторния gate.
        if self.decision == "cancel":
            return {"type": "ir.actions.act_window_close"}
        return self.picking_id.with_context(
            l10n_bg_waste_skip_check=True
        ).button_validate()


class WasteCodeWizardLine(models.TransientModel):
    _name = "l10n.bg.waste.code.wizard.line"
    _description = "Waste Code Entry Wizard - Line"

    wizard_id = fields.Many2one("l10n.bg.waste.code.wizard", required=True, ondelete="cascade")
    move_line_id = fields.Many2one("stock.move.line", required=True, readonly=True)
    product_id = fields.Many2one(related="move_line_id.product_id", readonly=True)
    quantity = fields.Float(related="move_line_id.quantity", readonly=True)
    product_uom_id = fields.Many2one(related="move_line_id.product_uom_id", readonly=True)
    waste_code_id = fields.Many2one(
        "l10n.bg.waste.code",
        string="Waste Code",
        required=True,
        domain="[('level','=','code')]",
    )
