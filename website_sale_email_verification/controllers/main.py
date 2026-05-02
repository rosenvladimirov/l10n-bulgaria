# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import urllib.parse

from odoo import http
from odoo.http import request
from odoo.addons.website_sale_no_public_order.controllers.main import (
    WebsiteSaleNoPublicOrder,
)

_logger = logging.getLogger(__name__)

PENDING_USER_SESSION_KEY = "shop_register_pending_user_id"


class WebsiteSaleEmailVerification(WebsiteSaleNoPublicOrder):

    # ── Step 1 override: disposable check + dispatch on company.method ────

    @http.route()
    def shop_register_post(
        self, name="", login="", password="", confirm_password="", **kwargs
    ):
        name = name.strip()
        login = login.strip()

        # Pre-flight validation: same set of errors as the parent so the user
        # sees a consistent error page if anything is missing. We re-implement
        # the validation here (instead of calling super first) because we
        # need to short-circuit on disposable email *before* any user is
        # created — calling super() would create the user and start sending
        # state-of-the-world side effects.
        error = None
        if not name:
            error = "name"
        elif not login:
            error = "email"
        elif password != confirm_password:
            error = "password_mismatch"
        elif len(password) < 6:
            error = "password_short"

        company = request.website.company_id or request.env.company
        if not error and company.email_verification_block_disposable:
            if request.env["disposable.email.domain"].sudo()._is_disposable(login):
                error = "disposable_email"

        if not error:
            existing = request.env["res.users"].sudo().search(
                [("login", "=ilike", login)], limit=1
            )
            if existing:
                error = "email_exists"

        if error:
            params = urllib.parse.urlencode(
                {"error": error, "name": name, "login": login}
            )
            return request.redirect("/shop/register?" + params)

        # Disabled mode: fall back to existing flow exactly as parent does.
        method = company.email_verification_method
        if method == "disabled":
            response = super().shop_register_post(
                name=name,
                login=login,
                password=password,
                confirm_password=confirm_password,
                **kwargs,
            )
            # Mark the freshly created user as verified — they didn't go
            # through verification but the field would otherwise default to
            # False and they'd hit a wall on the next install with method=otp.
            new_user = request.env["res.users"].sudo().search(
                [("login", "=ilike", login)], limit=1
            )
            if new_user:
                new_user.email_verified = True
            return response

        # Verification-enabled path. Create user, dispatch email, redirect to
        # the verify page; do NOT authenticate yet — the user must prove they
        # control the email first.
        try:
            portal_group = request.env.ref("base.group_portal")
            new_user = request.env["res.users"].sudo().create({
                "name": name,
                "login": login,
                "password": password,
                "groups_id": [(6, 0, [portal_group.id])],
                "email_verified": False,
            })
            if new_user.partner_id and not new_user.partner_id.email:
                new_user.partner_id.sudo().write({"email": login})
            new_user._send_verification_email()
            request.env.cr.commit()
        except Exception:
            _logger.exception(
                "Email-verified registration failed for login: %s", login,
            )
            params = urllib.parse.urlencode(
                {"error": "create_failed", "name": name, "login": login}
            )
            return request.redirect("/shop/register?" + params)

        request.session[PENDING_USER_SESSION_KEY] = new_user.id
        return request.redirect("/shop/register/verify")

    # ── Step 1.5 — verify page ────────────────────────────────────────────

    @http.route(
        "/shop/register/verify",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["GET"],
    )
    def shop_register_verify(self, error="", info="", **kwargs):
        user = self._verify_pending_user()
        if not user:
            return request.redirect("/shop/register")
        company = request.website.company_id or request.env.company
        ok, seconds_left = user._can_resend_verification()
        return request.render(
            "website_sale_email_verification.verify_step",
            {
                "method": company.email_verification_method,
                "email": user.login,
                "can_resend": ok,
                "cooldown_left": seconds_left,
                "error": error,
                "info": info,
            },
        )

    @http.route(
        "/shop/register/verify",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["POST"],
    )
    def shop_register_verify_post(self, otp="", **kwargs):
        from odoo import fields as odoo_fields  # local import for clarity

        user = self._verify_pending_user()
        if not user:
            return request.redirect("/shop/register")

        # Pre-check distinguishes "locked" (no hash → admin must reset) from
        # "expired" (hash present but past deadline) so the user gets a
        # readable error instead of just "invalid".
        if not user.email_verification_otp_hash:
            return self._verify_redirect("locked")
        if user.email_verification_expiry and \
                user.email_verification_expiry < odoo_fields.Datetime.now():
            return self._verify_redirect("expired")

        ok = user._verify_email_otp(otp.strip())
        if ok:
            return self._authenticate_and_continue(user)
        # _verify_email_otp clears the hash on max-attempts → re-classify
        # the failure as "locked" rather than "invalid".
        if not user.email_verification_otp_hash:
            return self._verify_redirect("locked")
        return self._verify_redirect("invalid_otp")

    # ── Step 1.5 — link verification ──────────────────────────────────────

    @http.route(
        "/shop/register/verify/link/<string:token>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["GET"],
    )
    def shop_register_verify_link(self, token, **kwargs):
        if not token:
            return request.redirect("/shop/register")
        user = request.env["res.users"].sudo().search(
            [("email_verification_token", "=", token)], limit=1,
        )
        if not user:
            return request.redirect("/shop/register/verify?error=invalid_token")
        if user.email_verified:
            return request.redirect("/shop/register/verify?info=already_verified")
        if not user._verify_email_token(token):
            return request.redirect("/shop/register/verify?error=expired")
        return self._authenticate_and_continue(user)

    # ── Step 1.5 — resend ─────────────────────────────────────────────────

    @http.route(
        "/shop/register/verify/resend",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["POST"],
    )
    def shop_register_verify_resend(self, **kwargs):
        user = self._verify_pending_user()
        if not user:
            return request.redirect("/shop/register")
        ok, _seconds = user._can_resend_verification()
        if not ok:
            return self._verify_redirect("cooldown")
        try:
            user._send_verification_email()
            request.env.cr.commit()
        except Exception:
            _logger.exception(
                "Resending verification mail failed for user %s.", user.login,
            )
            return self._verify_redirect("send_failed")
        return self._verify_redirect(info="sent")

    # ── helpers ────────────────────────────────────────────────────────────

    def _verify_pending_user(self):
        """Return the pending res.users record stored on the session, or
        False if the session has no pending registration."""
        user_id = request.session.get(PENDING_USER_SESSION_KEY)
        if not user_id:
            return False
        user = request.env["res.users"].sudo().browse(user_id).exists()
        if not user:
            request.session.pop(PENDING_USER_SESSION_KEY, None)
            return False
        return user

    def _verify_redirect(self, error="", info=""):
        params = {}
        if error:
            params["error"] = error
        if info:
            params["info"] = info
        suffix = ("?" + urllib.parse.urlencode(params)) if params else ""
        return request.redirect("/shop/register/verify" + suffix)

    def _authenticate_and_continue(self, user):
        """Drop the pending marker, log the user in and route them to Step 2.

        The link path arrives here without a password, so we cannot call
        ``request.session.authenticate(db, login, password)`` — instead we
        finalise the session by writing ``uid`` directly. This is safe
        because we have already verified ownership of the email at this
        point (token or OTP).
        """
        request.session.pop(PENDING_USER_SESSION_KEY, None)
        request.session.uid = user.id
        request.session.login = user.login
        request.update_env(user=user.id)
        return request.redirect("/shop/register/details")
