# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)

INFOPAY_WALLET_KEY = "infopay_access_token"


class Users(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, credential, user_agent_env):
        """After successful authentication, copy the InfoPay token into
        the logged-in user's wallet so they can use 'Fetch Data'."""
        result = super()._check_credentials(credential, user_agent_env)
        try:
            self._infopay_distribute_token()
        except Exception:
            # WARNING (not DEBUG) so an operator who suddenly cannot
            # use 'Fetch Data' has an audit-trail entry to look at.
            # Common causes: token-owner deactivated, wallet record
            # deleted, master password rotated without the wallet
            # being re-keyed.
            _logger.warning(
                "InfoPay token distribution skipped for user %s "
                "(check wallet integrity and l10n_bg_infopay_token_user_id "
                "on the company)", self.env.uid, exc_info=True,
            )
        return result

    def _infopay_distribute_token(self):
        """Copy the InfoPay access token from the owner's wallet into the
        authenticated user's wallet (re-encrypted with their password hash).
        """
        user = self.env.user
        company = user.company_id
        user_id = user.id

        # Skip if InfoPay is not configured on this company
        if not company.l10n_bg_infopay_unique_id or not company.l10n_bg_infopay_token_user_id:
            return

        owner_id = company.l10n_bg_infopay_token_user_id.id

        # Owner already has the token — nothing to do
        if owner_id == user_id:
            return

        Wallet = self.env["crypto.wallet"].sudo()

        # Check if user already has the token
        user_wallet = Wallet.search(
            [("user_id", "=", user_id), ("name", "=", "System Keys")],
            limit=1,
        )
        if user_wallet:
            try:
                user_wallet.get_key_with_user_password(INFOPAY_WALLET_KEY)
                return  # Already present
            except Exception:
                pass  # Not found — will copy below

        # Read token from owner's wallet
        owner_wallet = Wallet.search(
            [("user_id", "=", owner_id), ("name", "=", "System Keys")],
            limit=1,
        )
        if not owner_wallet:
            return

        try:
            token_data = owner_wallet.get_key_with_user_password(
                INFOPAY_WALLET_KEY
            )
        except Exception:
            _logger.warning(
                "Could not read InfoPay token from owner wallet (user %s)",
                owner_id,
            )
            return

        # Ensure the user has a wallet
        if not user_wallet:
            user_wallet = Wallet.get_user_wallet_or_create(user_id)

        # Store the token encrypted with the user's own password hash
        user_wallet.add_key_with_user_password(
            INFOPAY_WALLET_KEY, "api_key", token_data["data"]
        )
        _logger.info(
            "InfoPay token distributed to user %s from owner %s",
            user_id, owner_id,
        )
