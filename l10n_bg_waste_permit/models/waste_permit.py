# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Разрешително за третиране на отпадъци (чл. 35 / 67 / 78 ЗУО)."""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WastePermit(models.Model):
    _name = "l10n.bg.waste.permit"
    _description = "Bulgarian Waste Treatment Permit"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_issued desc, name"

    name = fields.Char(
        string="Permit Number",
        required=True,
        tracking=True,
        help="The number on the permit as issued (e.g. 'RD-XX-NNN' or 'KR-NN').",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    permit_type = fields.Selection(
        [
            ("art_67", "Treatment permit (WMA Art. 67)"),
            ("art_78", "Registration document (WMA Art. 78)"),
            ("ippc", "Integrated permit"),
        ],
        string="Permit Type",
        required=True,
        tracking=True,
    )
    issuing_authority = fields.Selection(
        [
            ("moew", "Ministry of Environment (MOEW)"),
            ("riosv", "Regional Inspectorate (RIOSV)"),
            ("iaos", "Executive Environment Agency (IAOS)"),
        ],
        string="Issuing Authority",
        tracking=True,
    )
    riosv_office = fields.Char(
        string="RIOSV Office",
        tracking=True,
        help="City of the regional inspectorate that issued the permit, "
             "when applicable (e.g. 'Vratsa', 'Sofia').",
    )
    date_issued = fields.Date(
        string="Date Issued",
        required=True,
        tracking=True,
    )
    date_valid_from = fields.Date(
        string="Valid From",
        tracking=True,
    )
    date_valid_to = fields.Date(
        string="Valid Until",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        default="draft",
        tracking=True,
        required=True,
    )
    line_ids = fields.One2many(
        "l10n.bg.waste.permit.line",
        "permit_id",
        string="Permitted Activities",
    )
    line_count = fields.Integer(
        compute="_compute_line_count",
        string="# Quota Rows",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "l10n_bg_waste_permit_attachment_rel",
        "permit_id",
        "attachment_id",
        string="Scanned Permit",
    )
    note = fields.Text()

    # --- Computes -----------------------------------------------------------
    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # --- Validation ---------------------------------------------------------
    @api.constrains("date_valid_from", "date_valid_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_valid_from and rec.date_valid_to and rec.date_valid_from > rec.date_valid_to:
                raise ValidationError(
                    _("Permit %s: validity start date cannot be after the end date.") % rec.name
                )

    # --- Workflow actions ---------------------------------------------------
    def action_activate(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(
                    _("Cannot activate permit %s with no permitted activities defined.") % rec.name
                )
            rec.state = "active"

    def action_suspend(self):
        self.write({"state": "suspended"})

    def action_revoke(self):
        self.write({"state": "revoked"})

    def action_set_to_draft(self):
        self.write({"state": "draft"})

    @api.model
    def cron_check_expiry(self):
        """Cron job: маркира активни разрешителни като 'expired', след като валидността изтече."""
        today = fields.Date.context_today(self)
        expired = self.search(
            [("state", "=", "active"), ("date_valid_to", "<", today)]
        )
        for rec in expired:
            rec.message_post(
                body=_("Permit auto-marked as expired (valid_to=%s).") % rec.date_valid_to,
                subtype_xmlid="mail.mt_note",
            )
        expired.write({"state": "expired"})
        return len(expired)
