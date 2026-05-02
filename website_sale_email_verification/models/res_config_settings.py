# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    email_verification_method = fields.Selection(
        related="company_id.email_verification_method",
        readonly=False,
    )
    email_verification_otp_length = fields.Integer(
        related="company_id.email_verification_otp_length",
        readonly=False,
    )
    email_verification_expiry_minutes = fields.Integer(
        related="company_id.email_verification_expiry_minutes",
        readonly=False,
    )
    email_verification_max_attempts = fields.Integer(
        related="company_id.email_verification_max_attempts",
        readonly=False,
    )
    email_verification_resend_cooldown = fields.Integer(
        related="company_id.email_verification_resend_cooldown",
        readonly=False,
    )
    email_verification_block_disposable = fields.Boolean(
        related="company_id.email_verification_block_disposable",
        readonly=False,
    )
    email_verification_disposable_url = fields.Char(
        related="company_id.email_verification_disposable_url",
        readonly=False,
    )

    def action_refresh_disposable_blocklist(self):
        """Trigger the disposable blocklist refresh from the settings page."""
        return self.env["disposable.email.domain"].action_refresh_now()
