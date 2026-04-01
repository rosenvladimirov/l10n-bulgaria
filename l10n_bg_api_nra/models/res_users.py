import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

NRA_WALLET_KEY_API_KEY = "nra_api_key"
NRA_WALLET_KEY_API_SECRET = "nra_api_secret"
NRA_WALLET_KEY_ACCESS_TOKEN = "nra_access_token"
NRA_WALLET_KEY_USER_PIN = "nra_user_pin"
NRA_WALLET_KEY_USER_SIGNATURE = "nra_user_signature"

NRA_WALLET_KEYS = (
    NRA_WALLET_KEY_API_KEY,
    NRA_WALLET_KEY_API_SECRET,
    NRA_WALLET_KEY_ACCESS_TOKEN,
    NRA_WALLET_KEY_USER_PIN,
    NRA_WALLET_KEY_USER_SIGNATURE,
)


class ResUsers(models.Model):
    _inherit = "res.users"

    @classmethod
    def _nra_distribute_credentials(cls, env, user_id):
        """Distribute NRA API credentials to the logging-in user's wallet.

        Called at login time. Copies the NRA API key, secret, and access
        token from the token owner's wallet to the current user's wallet,
        so every authorized user can make API calls during their session.

        :param env: Environment
        :param user_id: ID of the user logging in
        """
        Wallet = env["crypto.wallet"]

        # Find companies with NRA API enabled for this user
        companies = env["res.company"].sudo().search(
            [
                ("l10n_bg_nra_api_enabled", "=", True),
                ("l10n_bg_nra_token_user_id", "!=", False),
            ]
        )

        for company in companies:
            owner_id = company.l10n_bg_nra_token_user_id.id

            # Skip if the user IS the token owner (already has the keys)
            if owner_id == user_id:
                continue

            # Check if user already has NRA keys
            user_wallet = Wallet.search(
                [
                    ("user_id", "=", user_id),
                    ("name", "=", "System Keys"),
                ],
                limit=1,
            )
            if user_wallet:
                try:
                    user_wallet.get_key_with_user_password(NRA_WALLET_KEY_API_KEY)
                    continue  # Already has credentials
                except Exception:
                    pass  # Not found — will copy below

            # Read from owner's wallet
            owner_wallet = Wallet.search(
                [
                    ("user_id", "=", owner_id),
                    ("name", "=", "System Keys"),
                ],
                limit=1,
            )
            if not owner_wallet:
                continue

            # Ensure the user has a wallet
            if not user_wallet:
                user_wallet = Wallet.get_user_wallet_or_create(user_id)

            # Copy each NRA key to the user's wallet
            for key_name in NRA_WALLET_KEYS:
                try:
                    key_data = owner_wallet.get_key_with_user_password(key_name)
                    # Remove existing key if present (e.g. stale token)
                    try:
                        user_wallet.remove_key_with_user_password(key_name)
                    except Exception:
                        pass
                    user_wallet.add_key_with_user_password(
                        key_name, key_data.get("type", "api_key"), key_data["data"]
                    )
                except Exception:
                    _logger.debug(
                        "NRA key '%s' not found in owner wallet, skipping",
                        key_name,
                    )

            _logger.info(
                "NRA API credentials distributed to user %s for company %s",
                user_id,
                company.name,
            )

    @api.model
    def _check_credentials(self, password, env):
        """Override to distribute NRA credentials at login."""
        res = super()._check_credentials(password, env)
        try:
            self._nra_distribute_credentials(env, self.env.user.id)
        except Exception:
            _logger.debug(
                "NRA credential distribution failed for user %s",
                self.env.user.id,
                exc_info=True,
            )
        return res
