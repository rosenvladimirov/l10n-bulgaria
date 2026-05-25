# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Ред от разрешително: код × площадка × дейност × квоти.

Изчислява в реално време изразходвана и остатъчна квота чрез SQL агрегация
върху stock.move.line. Ако `l10n_bg_waste_picking` не е инсталиран
(колоната `waste_code_id` не съществува) — graceful degrade на нули.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WastePermitLine(models.Model):
    _name = "l10n.bg.waste.permit.line"
    _description = "Waste Permit Quota Line"
    _order = "permit_id, site_id, waste_code_id"

    permit_id = fields.Many2one(
        "l10n.bg.waste.permit",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="permit_id.company_id",
        store=True,
        index=True,
    )
    site_id = fields.Many2one(
        "l10n.bg.waste.site",
        string="Site",
        required=True,
        index=True,
        domain="[('company_id','=',company_id)]",
    )
    waste_code_id = fields.Many2one(
        "l10n.bg.waste.code",
        string="Waste Code",
        required=True,
        index=True,
        domain="[('level','=','code')]",
    )
    activity_id = fields.Many2one(
        "l10n.bg.waste.activity",
        string="Activity",
        required=True,
        index=True,
    )

    # --- Quota limits -------------------------------------------------------
    annual_quota_kg = fields.Float(
        string="Annual Quota (kg)",
        digits=(16, 3),
        help="Maximum quantity allowed to be treated under this code × site × "
             "activity for one calendar year.",
    )
    max_storage_kg = fields.Float(
        string="Max On-Site Storage (kg)",
        digits=(16, 3),
        help="Maximum amount of this waste code allowed to be stored at the "
             "site at any moment in time.",
    )

    # --- Real-time usage (computed) ----------------------------------------
    quota_used_ytd_kg = fields.Float(
        string="Used Year-to-Date (kg)",
        digits=(16, 3),
        compute="_compute_usage",
        help="Sum of accepted incoming waste pickings for this code × site, "
             "from January 1st of the current calendar year up to now.",
    )
    quota_remaining_kg = fields.Float(
        string="Remaining (kg)",
        digits=(16, 3),
        compute="_compute_usage",
    )
    quota_percent_used = fields.Float(
        string="Used (%)",
        compute="_compute_usage",
        help="quota_used_ytd_kg / annual_quota_kg × 100",
    )
    current_storage_kg = fields.Float(
        string="Currently On-Site (kg)",
        digits=(16, 3),
        compute="_compute_usage",
        help="Net of received minus delivered (or treated out) for the "
             "current year.",
    )

    # --- Constraints (Odoo 19: attribute name must start with '_') ---------
    _unique_per_permit = models.Constraint(
        "unique(permit_id, site_id, waste_code_id, activity_id)",
        "The same (site, waste code, activity) cannot appear twice in a permit.",
    )

    @api.constrains("annual_quota_kg", "max_storage_kg")
    def _check_non_negative(self):
        for rec in self:
            if rec.annual_quota_kg < 0:
                raise ValidationError(_("Annual quota cannot be negative."))
            if rec.max_storage_kg < 0:
                raise ValidationError(_("On-site storage limit cannot be negative."))

    # --- Compute (SQL aggregation) ----------------------------------------
    def _compute_usage(self):
        # Defensive default: ако picking модулът не е installed,
        # `stock.move.line.waste_code_id` не съществува → връщаме 0.
        if not self.ids:
            return
        sml_fields = self.env["stock.move.line"]._fields if "stock.move.line" in self.env else {}
        if "waste_code_id" not in sml_fields:
            for rec in self:
                rec.quota_used_ytd_kg = 0.0
                rec.current_storage_kg = 0.0
                rec.quota_remaining_kg = rec.annual_quota_kg or 0.0
                rec.quota_percent_used = 0.0
            return

        # Реална агрегация: количеството в килограми (waste_quantity_kg) от
        # завършени stock.move.line с дата >= 1 януари тек. година, чийто
        # destination warehouse е в свързаните warehouses на site_id.
        self.env.cr.execute(
            """
            WITH agg AS (
                SELECT
                    pl.id AS line_id,
                    COALESCE(SUM(sml.waste_quantity_kg)
                        FILTER (WHERE p.picking_type_code = 'incoming'), 0.0)
                        AS used_in_kg,
                    COALESCE(SUM(sml.waste_quantity_kg)
                        FILTER (WHERE p.picking_type_code = 'outgoing'), 0.0)
                        AS delivered_kg
                FROM l10n_bg_waste_permit_line pl
                LEFT JOIN stock_move_line sml
                       ON sml.waste_code_id = pl.waste_code_id
                      AND sml.state = 'done'
                LEFT JOIN stock_picking p
                       ON p.id = sml.picking_id
                      AND p.date_done >= date_trunc('year', CURRENT_DATE)
                      AND p.date_done <  date_trunc('year', CURRENT_DATE) + INTERVAL '1 year'
                LEFT JOIN l10n_bg_waste_site_warehouse_rel swr
                       ON swr.site_id = pl.site_id
                LEFT JOIN stock_location loc
                       ON loc.id = sml.location_dest_id
                      AND loc.warehouse_id = swr.warehouse_id
                WHERE pl.id IN %s
                GROUP BY pl.id
            )
            SELECT line_id, used_in_kg, delivered_kg FROM agg
            """,
            (tuple(self.ids),),
        )
        rows = {r[0]: (r[1] or 0.0, r[2] or 0.0) for r in self.env.cr.fetchall()}
        for rec in self:
            used_in, delivered = rows.get(rec.id, (0.0, 0.0))
            rec.quota_used_ytd_kg = used_in
            rec.current_storage_kg = used_in - delivered
            rec.quota_remaining_kg = (rec.annual_quota_kg or 0.0) - used_in
            rec.quota_percent_used = (
                (used_in / rec.annual_quota_kg * 100) if rec.annual_quota_kg else 0.0
            )

    # --- Helper API за picking модула --------------------------------------
    @api.model
    def _find_for(self, company_id, site_id, waste_code_id):
        """Намира активния permit line за дадена тройка. Връща empty recordset
        при липса. Picking модулът ползва това за валидиране при потвърждение.
        """
        return self.search(
            [
                ("company_id", "=", company_id),
                ("site_id", "=", site_id),
                ("waste_code_id", "=", waste_code_id),
                ("permit_id.state", "=", "active"),
            ],
            limit=1,
        )
