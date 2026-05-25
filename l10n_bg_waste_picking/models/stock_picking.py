# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Stock picking разширение: site, permit, ID документ + validate gate."""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# Прагови стойности за вдигане на warning/блокиращ alert.
_QUOTA_WARN_PERCENT = 80.0
_QUOTA_BLOCK_PERCENT = 100.0


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_waste_picking = fields.Boolean(
        string="Waste Picking",
        compute="_compute_is_waste_picking",
        store=True,
        index=True,
        help="Computed: True if any move line targets a product flagged "
             "as is_waste_product.",
    )
    waste_site_id = fields.Many2one(
        "l10n.bg.waste.site",
        string="Waste Site",
        domain="[('company_id','=',company_id)]",
        help="Site to which this picking is attributed for regulatory "
             "aggregation (Annex 4 monthly report).",
    )
    waste_permit_id = fields.Many2one(
        "l10n.bg.waste.permit",
        string="Permit",
        domain="[('state','=','active'),('company_id','=',company_id)]",
    )
    waste_transport_doc = fields.Char(
        string="Transport / ID Document #",
        help="Number of the freight or identification document (Annex 8 "
             "for hazardous shipments).",
    )
    waste_vehicle_plate = fields.Char(string="Vehicle Plate")
    waste_id_document_id = fields.Many2one(
        "l10n.bg.waste.id.document",
        string="Annex 8 ID Document",
        help="Required for hazardous waste transport per Art. 12 of "
             "Ordinance 1/2014.",
    )

    @api.depends("move_ids.product_id.is_waste_product")
    def _compute_is_waste_picking(self):
        for picking in self:
            picking.is_waste_picking = any(
                m.product_id.is_waste_product for m in picking.move_ids
            )

    # ------------------------------------------------------------------
    # Validate gate: required code → wizard; quota breach → block.
    # ------------------------------------------------------------------
    def button_validate(self):
        # Допуска повторно влизане през wizard.action_apply() с context flag.
        if self.env.context.get("l10n_bg_waste_skip_check"):
            return super().button_validate()

        # 1) Изисквай код за всеки waste move.line.
        missing = self._l10n_bg_waste_missing_codes()
        if missing:
            return self._l10n_bg_waste_open_code_wizard(missing)

        # 2) Провери квота — над 100% блокира (до изричен override).
        breach = self._l10n_bg_waste_check_quota()
        if breach:
            # Wizard-ът ще покаже warning + decision (proceed/cancel).
            return self._l10n_bg_waste_open_code_wizard(quota_breach=breach)

        return super().button_validate()

    # --- Helpers ------------------------------------------------------
    def _l10n_bg_waste_missing_codes(self):
        """Връща recordset move.line-ове без code за продукти-отпадък."""
        return self.move_line_ids.filtered(
            lambda ml: ml.product_id.is_waste_product and not ml.waste_code_id
        )

    def _l10n_bg_waste_check_quota(self):
        """Връща списък dict-ове с информация за линиите над прага.

        Връща празен списък ако всичко е в нормата.
        """
        breaches = []
        if not self.waste_site_id:
            return breaches
        # Групирай move.line-овете по код за тази площадка.
        line_obj = self.env["l10n.bg.waste.permit.line"]
        by_code = {}
        for ml in self.move_line_ids:
            if not ml.waste_code_id or not ml.waste_quantity_kg:
                continue
            by_code.setdefault(ml.waste_code_id.id, 0.0)
            by_code[ml.waste_code_id.id] += ml.waste_quantity_kg
        for code_id, incoming_kg in by_code.items():
            pl = line_obj._find_for(self.company_id.id, self.waste_site_id.id, code_id)
            if not pl:
                continue
            future_used = (pl.quota_used_ytd_kg or 0.0) + incoming_kg
            percent = (future_used / pl.annual_quota_kg * 100) if pl.annual_quota_kg else 0.0
            if percent >= _QUOTA_WARN_PERCENT:
                breaches.append({
                    "permit_line_id": pl.id,
                    "waste_code_id": code_id,
                    "incoming_kg": incoming_kg,
                    "ytd_kg": pl.quota_used_ytd_kg,
                    "annual_quota_kg": pl.annual_quota_kg,
                    "future_used_kg": future_used,
                    "future_percent": percent,
                    "is_block": percent >= _QUOTA_BLOCK_PERCENT,
                })
        return breaches

    def _l10n_bg_waste_open_code_wizard(self, missing_lines=None, quota_breach=None):
        """Отваря wizard за въвеждане на код и/или решение при превишена квота."""
        Wizard = self.env["l10n.bg.waste.code.wizard"]
        wiz = Wizard.create({
            "picking_id": self.id,
            "line_ids": [
                (0, 0, {
                    "move_line_id": ml.id,
                    "waste_code_id": ml.product_id.product_tmpl_id.default_waste_code_id.id or False,
                })
                for ml in (missing_lines or self.move_line_ids.filtered(
                    lambda l: l.product_id.is_waste_product
                ))
            ],
            "quota_breach_json": str(quota_breach or []),
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Waste Code Entry"),
            "res_model": "l10n.bg.waste.code.wizard",
            "res_id": wiz.id,
            "view_mode": "form",
            "target": "new",
        }

    def _l10n_bg_waste_post_acceptance(self, decision=None, note=None):
        """Логва в chatter завършеното приемане + (евент.) override бележка.

        decision: 'normal' | 'warning_80' | 'over_quota'
        """
        for picking in self:
            lines_html = []
            for ml in picking.move_line_ids.filtered(lambda l: l.waste_code_id):
                lines_html.append(
                    f"<li><b>{ml.waste_code_id.code}</b> — "
                    f"{ml.waste_quantity_kg:.3f} kg "
                    f"({ml.product_id.display_name})</li>"
                )
            body = "<p><b>%s</b></p><ul>%s</ul>" % (
                _("Waste shipment accepted"),
                "".join(lines_html) or _("(no waste lines)")
            )
            if decision in ("warning_80", "over_quota") and note:
                body += "<p><b>%s:</b> %s</p>" % (_("Override note"), note)
            picking.message_post(body=body, subtype_xmlid="mail.mt_note")

            # Activity до отговорника при превишение.
            if decision == "over_quota":
                wm = picking.company_id.waste_manager_id
                if wm:
                    picking.activity_schedule(
                        "mail.mail_activity_data_warning",
                        user_id=wm.id,
                        summary=_("Quota exceeded at site %s") % (
                            picking.waste_site_id.name or "?"
                        ),
                        note=note or "",
                    )
