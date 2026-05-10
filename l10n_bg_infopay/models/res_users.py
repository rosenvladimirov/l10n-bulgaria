# Copyright 2025-2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)

INFOPAY_WALLET_UNIQUE_ID_KEY = "infopay_unique_id"
INFOPAY_WALLET_ACCESS_TOKEN_KEY = "infopay_access_token"


class Users(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, credential, user_agent_env):
        """After successful auth, copy the InfoPay credentials into the
        logged-in user's wallet so they can use 'Fetch Data' without
        knowing the original setup user's password.
        """
        result = super()._check_credentials(credential, user_agent_env)
        try:
            self._infopay_distribute_token()
        except Exception:
            # WARNING (not DEBUG) so an operator who suddenly cannot
            # use 'Fetch Data' has an audit-trail entry to look at.
            _logger.warning(
                "InfoPay token distribution skipped for user %s "
                "(check wallet integrity and l10n_bg_infopay_token_user_id "
                "on the company)", self.env.uid, exc_info=True,
            )
        return result

    def _infopay_distribute_token(self):
        """Copy BOTH InfoPay credentials (uniqueId + accessToken) from
        the owner's wallet into the authenticated user's wallet
        (re-encrypted with their password hash).
        """
        user = self.env.user
        company = user.company_id
        user_id = user.id

        # Skip if InfoPay is not configured on this company.
        if not company.l10n_bg_infopay_token_user_id:
            return

        owner_id = company.l10n_bg_infopay_token_user_id.id
        if owner_id == user_id:
            return  # Owner already has the credentials

        Wallet = self.env["crypto.wallet"].sudo()

        user_wallet = Wallet.search(
            [("user_id", "=", user_id), ("name", "=", "System Keys")],
            limit=1,
        )
        # Both keys already present? Skip the copy.
        if user_wallet:
            try:
                user_wallet.get_key_with_user_password(
                    INFOPAY_WALLET_UNIQUE_ID_KEY,
                )
                user_wallet.get_key_with_user_password(
                    INFOPAY_WALLET_ACCESS_TOKEN_KEY,
                )
                return
            except Exception:
                pass  # One or both missing — copy below

        owner_wallet = Wallet.search(
            [("user_id", "=", owner_id), ("name", "=", "System Keys")],
            limit=1,
        )
        if not owner_wallet:
            return

        try:
            uid_data = owner_wallet.get_key_with_user_password(
                INFOPAY_WALLET_UNIQUE_ID_KEY,
            )
            tok_data = owner_wallet.get_key_with_user_password(
                INFOPAY_WALLET_ACCESS_TOKEN_KEY,
            )
        except Exception:
            _logger.warning(
                "Could not read InfoPay credentials from owner wallet "
                "(user %s)", owner_id,
            )
            return

        if not user_wallet:
            user_wallet = Wallet.get_user_wallet_or_create(user_id)

        user_wallet.add_key_with_user_password(
            INFOPAY_WALLET_UNIQUE_ID_KEY, "api_key", uid_data["data"],
        )
        user_wallet.add_key_with_user_password(
            INFOPAY_WALLET_ACCESS_TOKEN_KEY, "api_key", tok_data["data"],
        )
        _logger.info(
            "InfoPay credentials distributed to user %s from owner %s",
            user_id, owner_id,
        )
