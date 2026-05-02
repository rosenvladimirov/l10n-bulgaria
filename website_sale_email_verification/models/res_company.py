# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    email_verification_method = fields.Selection(
        [
            ("disabled", "Disabled"),
            ("link", "Link"),
            ("otp", "One-Time Code (OTP)"),
            ("both", "Link and OTP"),
        ],
        string="Email Verification Method",
        default="disabled",
        required=True,
        help="How shop registrants verify their email between Step 1 and "
             "Step 2 of the wizard. 'Disabled' keeps the existing two-step "
             "flow untouched.",
    )
    email_verification_otp_length = fields.Integer(
        string="OTP Length",
        default=6,
        help="Number of digits in the one-time code (4–8).",
    )
    email_verification_expiry_minutes = fields.Integer(
        string="Verification Expiry (minutes)",
        default=30,
        help="How long a token / OTP stays valid after being sent.",
    )
    email_verification_max_attempts = fields.Integer(
        string="Max OTP Attempts",
        default=5,
        help="Number of wrong OTP entries before the account is locked.",
    )
    email_verification_resend_cooldown = fields.Integer(
        string="Resend Cooldown (seconds)",
        default=60,
        help="Minimum delay between two consecutive resend requests.",
    )
    email_verification_block_disposable = fields.Boolean(
        string="Block Disposable Email Providers",
        default=True,
        help="Reject Mailinator, 10minutemail, GuerrillaMail and similar "
             "domains during shop registration.",
    )
    email_verification_disposable_url = fields.Char(
        string="Disposable Blocklist Source URL",
        default="https://raw.githubusercontent.com/disposable-email-domains/"
                "disposable-email-domains/master/disposable_email_blocklist.conf",
        help="Upstream source for the weekly cron refresh of the disposable "
             "email blocklist.",
    )
