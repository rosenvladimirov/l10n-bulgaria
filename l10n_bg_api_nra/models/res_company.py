import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

NRA_WALLET_KEY_API_KEY = "nra_api_key"
NRA_WALLET_KEY_API_SECRET = "nra_api_secret"
NRA_WALLET_KEY_ACCESS_TOKEN = "nra_access_token"
NRA_WALLET_KEY_USER_PIN = "nra_user_pin"
NRA_WALLET_KEY_USER_SIGNATURE = "nra_user_signature"

NRA_PIN_TYPE_SELECTION = [
    ("IND_EGN", "ЕГН"),
    ("IND_LNCH", "ЛН/ЛНЧ"),
    ("IND_SLNO", "Служебен номер"),
    ("IND_BULSTAT", "ЕИК по БУЛСТАТ на ФЛ"),
    ("BUS_BULSTAT", "ЕИК по Булстат/ЕИК по ЗТРРЮЛНЦ"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    # ------------------------------------------------------------------
    # NRA API configuration (non-secret fields stay in DB)
    # ------------------------------------------------------------------

    l10n_bg_nra_api_enabled = fields.Boolean(
        string="NRA API Enabled",
        default=False,
    )
    l10n_bg_nra_auth_mode = fields.Selection(
        selection=[
            ("oauth", "OAuth 2.0 (Client ID + Secret)"),
            ("direct_token", "Direct Token (Client ID + JWT)"),
        ],
        string="NRA Auth Mode",
        default="oauth",
        help="OAuth requires client_id + client_secret. "
             "Direct Token uses a pre-generated JWT access token.",
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
    l10n_bg_nra_taxpayer_pin_type = fields.Selection(
        selection=NRA_PIN_TYPE_SELECTION,
        string="Taxpayer PIN Type (Тип идентификатор на ЗЛ)",
        default="BUS_BULSTAT",
        help="Type of taxpayer identifier sent to NRA API.",
    )
    l10n_bg_nra_user_pin_type = fields.Selection(
        selection=NRA_PIN_TYPE_SELECTION,
        string="User PIN Type (Тип идентификатор на потребител)",
        default="IND_EGN",
        help="Type of user identifier for the person submitting declarations.",
    )
    l10n_bg_nra_insurance_fund = fields.Selection(
        selection=[("0", "Не"), ("1", "Да")],
        string="Insurance Fund (Осигурителна каса)",
        default="0",
        help="Whether declarations are submitted from an insurance fund (осигурителна каса).",
    )

    # ------------------------------------------------------------------
    # Wallet-based credential management
    # ------------------------------------------------------------------

    def _nra_set_credentials(self, api_key, api_secret, user_pin=None,
                             user_signature=None):
        """Store NRA API credentials in the current user's crypto wallet.

        :param api_key: NRA API key (client_id)
        :param api_secret: NRA API secret (client_secret)
        :param user_pin: User identifier (ЕГН/ЛНЧ) for declaration submission
        :param user_signature: Base64 encoded user certificate (КЕП)
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]
        wallet = Wallet.get_user_wallet_or_create()

        # Remove old keys if they exist
        for key_name in (
            NRA_WALLET_KEY_API_KEY,
            NRA_WALLET_KEY_API_SECRET,
            NRA_WALLET_KEY_USER_PIN,
            NRA_WALLET_KEY_USER_SIGNATURE,
        ):
            try:
                wallet.remove_key_with_user_password(key_name)
            except Exception:
                pass

        wallet.add_key_with_user_password(
            NRA_WALLET_KEY_API_KEY, "api_key", api_key
        )
        wallet.add_key_with_user_password(
            NRA_WALLET_KEY_API_SECRET, "api_key", api_secret
        )
        if user_pin:
            wallet.add_key_with_user_password(
                NRA_WALLET_KEY_USER_PIN, "api_key", user_pin
            )
        if user_signature:
            wallet.add_key_with_user_password(
                NRA_WALLET_KEY_USER_SIGNATURE, "certificate", user_signature
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

    def _nra_get_user_credentials(self):
        """Retrieve NRA user PIN and certificate from crypto wallet.

        :returns: tuple (user_pin, user_signature_base64)
        :raises UserError: if credentials not found
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]

        # Try current user's wallet first
        for wallet_search in [
            [("user_id", "=", self.env.user.id), ("name", "=", "System Keys")],
            [("user_id", "=", self.l10n_bg_nra_token_user_id.id), ("name", "=", "System Keys")]
            if self.l10n_bg_nra_token_user_id and self.l10n_bg_nra_token_user_id.id != self.env.user.id
            else None,
        ]:
            if not wallet_search:
                continue
            wallet = Wallet.sudo().search(wallet_search, limit=1)
            if wallet:
                try:
                    pin_data = wallet.get_key_with_user_password(
                        NRA_WALLET_KEY_USER_PIN
                    )
                    sig_data = wallet.get_key_with_user_password(
                        NRA_WALLET_KEY_USER_SIGNATURE
                    )
                    return pin_data["data"], sig_data["data"]
                except Exception:
                    pass

        raise UserError(
            _(
                "NRA user credentials (ЕГН and КЕП certificate) not found "
                "for company '%s'. Please configure them in Settings → NRA API.",
                self.name,
            )
        )

    def _nra_set_direct_token(self, client_id, access_token):
        """Store a pre-generated JWT access token directly.

        Parses the JWT exp claim to determine expiry. Stores in wallet
        if available, otherwise falls back to ir.config_parameter.

        :param client_id: NRA client_id
        :param access_token: Pre-generated JWT bearer token
        """
        import base64
        import json

        self.ensure_one()

        # Try wallet storage first
        try:
            Wallet = self.env["crypto.wallet"]
            wallet = Wallet.get_user_wallet_or_create()
            for key_name in (NRA_WALLET_KEY_API_KEY, NRA_WALLET_KEY_ACCESS_TOKEN):
                try:
                    wallet.remove_key_with_user_password(key_name)
                except Exception:
                    pass
            wallet.add_key_with_user_password(
                NRA_WALLET_KEY_API_KEY, "api_key", client_id
            )
            wallet.add_key_with_user_password(
                NRA_WALLET_KEY_ACCESS_TOKEN, "token", access_token
            )
        except Exception:
            _logger.info("Wallet unavailable, storing token in system parameters")

        # Always store in ir.config_parameter as fallback
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("l10n_bg_nra.direct_token", access_token)
        ICP.set_param("l10n_bg_nra.client_id", client_id)

        # Parse JWT exp claim for expiry
        try:
            payload = access_token.split(".")[1]
            payload += "=" * (4 - len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            exp_timestamp = claims.get("exp", 0)
            from datetime import datetime
            token_expiry = datetime.utcfromtimestamp(exp_timestamp)
        except Exception:
            token_expiry = fields.Datetime.add(fields.Datetime.now(), days=365)

        self.sudo().write({
            "l10n_bg_nra_auth_mode": "direct_token",
            "l10n_bg_nra_token_expiry": token_expiry,
            "l10n_bg_nra_token_user_id": self.env.user.id,
        })
        _logger.info(
            "NRA direct token stored for company %s (expires %s)",
            self.name,
            token_expiry,
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

        # Fallback to ir.config_parameter for direct_token mode
        if self.l10n_bg_nra_auth_mode == "direct_token":
            token = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("l10n_bg_nra.direct_token", False)
            )
            if token:
                return token

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
            NRA_WALLET_KEY_USER_PIN,
            NRA_WALLET_KEY_USER_SIGNATURE,
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
