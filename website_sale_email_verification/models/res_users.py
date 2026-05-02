# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _hash_otp(otp):
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


class ResUsers(models.Model):
    _inherit = "res.users"

    email_verified = fields.Boolean(
        string="Email Verified",
        default=False,
        help="Set to True once the user has confirmed their email through "
             "the shop registration verification flow.",
    )
    email_verification_token = fields.Char(
        string="Verification Token",
        copy=False,
        index=True,
    )
    email_verification_otp_hash = fields.Char(
        string="Verification OTP (SHA-256)",
        copy=False,
        help="SHA-256 hex digest of the current one-time code. The raw OTP "
             "is never stored.",
    )
    email_verification_expiry = fields.Datetime(
        string="Verification Expiry",
        copy=False,
    )
    email_verification_attempts = fields.Integer(
        string="Verification Attempts",
        default=0,
        copy=False,
    )
    email_verification_last_sent = fields.Datetime(
        string="Verification Last Sent",
        copy=False,
    )

    # ── credential generation / sending ────────────────────────────────────

    def _generate_verification_credentials(self):
        """Create a fresh token + OTP and persist (hashed) on the user.

        Returns ``{'token': str, 'otp': str}`` where ``otp`` is the *raw*
        code intended for the email body only — it must NEVER be persisted.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        otp_length = max(4, min(8, company.email_verification_otp_length or 6))
        expiry_minutes = company.email_verification_expiry_minutes or 30

        otp_int = secrets.randbelow(10 ** otp_length)
        otp = str(otp_int).zfill(otp_length)
        token = secrets.token_urlsafe(32)

        self.sudo().write({
            "email_verification_token": token,
            "email_verification_otp_hash": _hash_otp(otp),
            "email_verification_expiry": fields.Datetime.now() + timedelta(
                minutes=expiry_minutes,
            ),
            "email_verification_attempts": 0,
            "email_verification_last_sent": fields.Datetime.now(),
        })
        return {"token": token, "otp": otp}

    def _send_verification_email(self):
        """Generate fresh credentials and dispatch the verification email."""
        self.ensure_one()
        company = self.company_id or self.env.company
        method = company.email_verification_method
        if method == "disabled":
            return False

        creds = self._generate_verification_credentials()
        template = self.env.ref(
            "website_sale_email_verification.mail_template_email_verification",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "Email verification template missing — cannot send mail "
                "for user %s.",
                self.login,
            )
            return False

        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", "",
        )
        verify_url = "%s/shop/register/verify/link/%s" % (
            base_url.rstrip("/"),
            creds["token"],
        )
        ctx = {
            "show_otp": method in ("otp", "both"),
            "show_link": method in ("link", "both"),
            "otp": creds["otp"],
            "verify_url": verify_url,
            "expiry_minutes": company.email_verification_expiry_minutes,
        }
        template.with_context(**ctx).sudo().send_mail(
            self.id, force_send=True,
        )
        return True

    # ── verification ───────────────────────────────────────────────────────

    def _clear_verification_state(self, mark_verified):
        """Atomic clear of all five verification fields. ``mark_verified``
        controls the new state of ``email_verified``.
        """
        self.sudo().write({
            "email_verified": mark_verified,
            "email_verification_token": False,
            "email_verification_otp_hash": False,
            "email_verification_expiry": False,
            "email_verification_attempts": 0,
            # Keep email_verification_last_sent intact for cooldown auditing.
        })

    def _verify_email_otp(self, code):
        """Constant-time compare ``code`` against the stored OTP hash.

        On failure: increment attempts; if attempts >= max → clear OTP/token
        (account locked until admin action or new credentials are sent).
        On success: clear all verification fields and set
        ``email_verified=True``.
        """
        self.ensure_one()
        if not code or not self.email_verification_otp_hash:
            return False
        if self.email_verification_expiry and \
                self.email_verification_expiry < fields.Datetime.now():
            return False

        candidate = _hash_otp(str(code).strip())
        if hmac.compare_digest(candidate, self.email_verification_otp_hash):
            self._clear_verification_state(mark_verified=True)
            return True

        attempts = (self.email_verification_attempts or 0) + 1
        max_attempts = (self.company_id or self.env.company).\
            email_verification_max_attempts or 5
        if attempts >= max_attempts:
            self.sudo().write({
                "email_verification_otp_hash": False,
                "email_verification_token": False,
                "email_verification_attempts": attempts,
            })
        else:
            self.sudo().write({
                "email_verification_attempts": attempts,
            })
        return False

    def _verify_email_token(self, token):
        """Constant-time compare ``token`` against the stored verification
        token. Returns True on success and clears the state.
        """
        self.ensure_one()
        if not token or not self.email_verification_token:
            return False
        if self.email_verification_expiry and \
                self.email_verification_expiry < fields.Datetime.now():
            return False
        if hmac.compare_digest(
            str(token), str(self.email_verification_token),
        ):
            self._clear_verification_state(mark_verified=True)
            return True
        return False

    def _can_resend_verification(self):
        """Cooldown check. Returns ``(ok: bool, seconds_remaining: int)``."""
        self.ensure_one()
        cooldown = (self.company_id or self.env.company).\
            email_verification_resend_cooldown or 60
        last = self.email_verification_last_sent
        if not last:
            return True, 0
        elapsed = (fields.Datetime.now() - last).total_seconds()
        if elapsed >= cooldown:
            return True, 0
        return False, int(cooldown - elapsed)

    # ── admin actions on the user form ─────────────────────────────────────

    def action_force_email_verified(self):
        """Admin: bypass verification for this user."""
        self.ensure_one()
        self._clear_verification_state(mark_verified=True)
        return True

    def action_reset_email_verification(self):
        """Admin: clear verification, generate new credentials, resend mail."""
        self.ensure_one()
        self.sudo().write({"email_verified": False})
        self._send_verification_email()
        return True


class ResUsersInit(models.AbstractModel):
    """Tiny helper used by the post_init hook — kept here to avoid a
    standalone module just for one helper."""
    _name = "website_sale_email_verification.init"
    _description = "Email verification post-init helper"
