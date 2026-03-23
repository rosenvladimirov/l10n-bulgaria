import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

NRA_WALLET_KEY_API_KEY = "nra_api_key"
NRA_WALLET_KEY_API_SECRET = "nra_api_secret"
NRA_WALLET_KEY_ACCESS_TOKEN = "nra_access_token"


class ResCompany(models.Model):
    _inherit = "res.company"

    # ------------------------------------------------------------------
    # NRA API configuration (non-secret fields stay in DB)
    # ------------------------------------------------------------------

    l10n_bg_nra_api_enabled = fields.Boolean(
        string="NRA API Enabled",
        default=False,
    )
    l10n_bg_nra_test_mode = fields.Boolean(
        string="NRA API Test Mode",
        default=True,
        help="Use the NRA test environment for API calls.",
    )
    l10n_bg_nra_token_expiry = fields.Datetime(
        string="Token Expiry",
        copy=False,
    )
    l10n_bg_nra_token_user_id = fields.Many2one(
        "res.users",
        string="NRA Token Owner",
        copy=False,
        help="User who stored the NRA API credentials.",
    )

    # ------------------------------------------------------------------
    # Wallet-based credential management
    # ------------------------------------------------------------------

    def _nra_set_credentials(self, api_key, api_secret):
        """Store NRA API credentials in the current user's crypto wallet.

        :param api_key: NRA API key (client_id)
        :param api_secret: NRA API secret (client_secret)
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]
        wallet = Wallet.get_user_wallet_or_create()

        # Remove old keys if they exist
        try:
            wallet.remove_key_with_user_password(NRA_WALLET_KEY_API_KEY)
        except Exception:
            pass
        try:
            wallet.remove_key_with_user_password(NRA_WALLET_KEY_API_SECRET)
        except Exception:
            pass

        wallet.add_key_with_user_password(
            NRA_WALLET_KEY_API_KEY, "api_key", api_key
        )
        wallet.add_key_with_user_password(
            NRA_WALLET_KEY_API_SECRET, "api_key", api_secret
        )
        self.write({
            "l10n_bg_nra_token_user_id": self.env.user.id,
        })
        _logger.info(
            "NRA API credentials stored in wallet for company %s by user %s",
            self.name,
            self.env.user.name,
        )

    def _nra_get_credentials(self):
        """Retrieve NRA API credentials from crypto wallet.

        Tries the current user's wallet first, then falls back to
        the token owner's wallet (for cron jobs / other users).

        :returns: tuple (api_key, api_secret)
        :raises UserError: if credentials not found
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]

        # Try current user's wallet first
        user_wallet = Wallet.search(
            [
                ("user_id", "=", self.env.user.id),
                ("name", "=", "System Keys"),
            ],
            limit=1,
        )
        if user_wallet:
            try:
                api_key_data = user_wallet.get_key_with_user_password(
                    NRA_WALLET_KEY_API_KEY
                )
                api_secret_data = user_wallet.get_key_with_user_password(
                    NRA_WALLET_KEY_API_SECRET
                )
                return api_key_data["data"], api_secret_data["data"]
            except Exception:
                pass

        # Fallback to token owner's wallet
        token_user = self.l10n_bg_nra_token_user_id
        if token_user and token_user.id != self.env.user.id:
            owner_wallet = Wallet.sudo().search(
                [
                    ("user_id", "=", token_user.id),
                    ("name", "=", "System Keys"),
                ],
                limit=1,
            )
            if owner_wallet:
                try:
                    api_key_data = owner_wallet.get_key_with_user_password(
                        NRA_WALLET_KEY_API_KEY
                    )
                    api_secret_data = owner_wallet.get_key_with_user_password(
                        NRA_WALLET_KEY_API_SECRET
                    )
                    return api_key_data["data"], api_secret_data["data"]
                except Exception:
                    pass

        raise UserError(
            _(
                "NRA API credentials not found for company '%s'. "
                "Please configure them in Settings → NRA API.",
                self.name,
            )
        )

    def _nra_store_access_token(self, access_token, expires_in=3600):
        """Store the OAuth2 access token in the crypto wallet.

        :param access_token: Bearer token string
        :param expires_in: Token lifetime in seconds
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]
        wallet = Wallet.get_user_wallet_or_create()

        # Remove old token if exists
        try:
            wallet.remove_key_with_user_password(NRA_WALLET_KEY_ACCESS_TOKEN)
        except Exception:
            pass

        wallet.add_key_with_user_password(
            NRA_WALLET_KEY_ACCESS_TOKEN, "token", access_token
        )
        self.sudo().write(
            {
                "l10n_bg_nra_token_expiry": fields.Datetime.add(
                    fields.Datetime.now(), seconds=expires_in - 60
                ),
            }
        )

    def _nra_get_access_token(self):
        """Retrieve the cached OAuth2 access token from wallet.

        :returns: access token string or False if not found/expired
        """
        self.ensure_one()

        # Check expiry first
        if (
            not self.l10n_bg_nra_token_expiry
            or self.l10n_bg_nra_token_expiry <= fields.Datetime.now()
        ):
            return False

        Wallet = self.env["crypto.wallet"]

        # Try current user's wallet
        user_wallet = Wallet.search(
            [
                ("user_id", "=", self.env.user.id),
                ("name", "=", "System Keys"),
            ],
            limit=1,
        )
        if user_wallet:
            try:
                token_data = user_wallet.get_key_with_user_password(
                    NRA_WALLET_KEY_ACCESS_TOKEN
                )
                return token_data["data"]
            except Exception:
                pass

        # Fallback to token owner's wallet
        token_user = self.l10n_bg_nra_token_user_id
        if token_user and token_user.id != self.env.user.id:
            owner_wallet = Wallet.sudo().search(
                [
                    ("user_id", "=", token_user.id),
                    ("name", "=", "System Keys"),
                ],
                limit=1,
            )
            if owner_wallet:
                try:
                    token_data = owner_wallet.get_key_with_user_password(
                        NRA_WALLET_KEY_ACCESS_TOKEN
                    )
                    return token_data["data"]
                except Exception:
                    pass

        return False

    def _nra_clear_credentials(self):
        """Remove all NRA credentials from wallet."""
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]
        wallet = Wallet.get_user_wallet_or_create()
        for key_name in (
            NRA_WALLET_KEY_API_KEY,
            NRA_WALLET_KEY_API_SECRET,
            NRA_WALLET_KEY_ACCESS_TOKEN,
        ):
            try:
                wallet.remove_key_with_user_password(key_name)
            except Exception:
                pass
        self.sudo().write(
            {
                "l10n_bg_nra_token_expiry": False,
                "l10n_bg_nra_token_user_id": False,
            }
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_nra_test_connection(self):
        """Test the NRA API connection with current credentials."""
        self.ensure_one()
        provider = self.env["nra.api.provider"]
        try:
            provider._obtain_access_token(self)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("NRA API Connection"),
                    "message": _("Connection successful! Token obtained."),
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as exc:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("NRA API Connection"),
                    "message": _("Connection failed: %s", exc),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_nra_clear_token(self):
        """Clear the cached NRA API token from wallet."""
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]
        wallet = Wallet.get_user_wallet_or_create()
        try:
            wallet.remove_key_with_user_password(NRA_WALLET_KEY_ACCESS_TOKEN)
        except Exception:
            pass
        self.sudo().write({"l10n_bg_nra_token_expiry": False})
