import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NraCredentialsWizard(models.TransientModel):
    _name = "nra.credentials.wizard"
    _description = "NRA API Credentials Setup"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    auth_mode = fields.Selection(
        selection=[
            ("oauth", "OAuth 2.0 (Client ID + Secret)"),
            ("direct_token", "Direct Token (Client ID + JWT)"),
        ],
        string="Authentication Mode",
        default="oauth",
        required=True,
    )
    api_key = fields.Char(
        string="API Key (Client ID)",
        required=True,
    )
    api_secret = fields.Char(
        string="API Secret (Client Secret)",
    )
    access_token = fields.Text(
        string="Access Token (JWT)",
        help="Pre-generated JWT bearer token from NRA.",
    )
    user_pin = fields.Char(
        string="User PIN (ЕГН/ЛНЧ на подаващия)",
        help="Personal identifier (ЕГН or ЛНЧ) of the person authorized "
             "to submit declarations. Must match the КЕП certificate.",
    )
    user_signature = fields.Text(
        string="User Certificate (КЕП Base64)",
        help="Base64-encoded public certificate from the Qualified Electronic "
             "Signature (КЕП). Remove the BEGIN/END CERTIFICATE lines and "
             "all newlines before pasting.",
    )

    def action_save_credentials(self):
        """Save NRA API credentials to the crypto wallet."""
        self.ensure_one()

        if self.auth_mode == "oauth":
            if not self.api_key or not self.api_secret:
                raise UserError(_("Both API Key and API Secret are required for OAuth mode."))
            self.company_id._nra_set_credentials(
                self.api_key,
                self.api_secret,
                user_pin=self.user_pin or None,
                user_signature=self.user_signature or None,
            )
        else:
            if not self.api_key or not self.access_token:
                raise UserError(_("Both Client ID and Access Token are required for Direct Token mode."))
            self.company_id._nra_set_direct_token(
                self.api_key,
                self.access_token.strip(),
            )
            # Store user credentials separately if provided
            if self.user_pin or self.user_signature:
                from odoo.addons.l10n_bg_api_nra.models.res_company import (
                    NRA_WALLET_KEY_USER_PIN,
                    NRA_WALLET_KEY_USER_SIGNATURE,
                )
                Wallet = self.env["crypto.wallet"]
                wallet = Wallet.get_user_wallet_or_create()
                if self.user_pin:
                    try:
                        wallet.remove_key_with_user_password(NRA_WALLET_KEY_USER_PIN)
                    except Exception:
                        pass
                    wallet.add_key_with_user_password(
                        NRA_WALLET_KEY_USER_PIN, "api_key", self.user_pin
                    )
                if self.user_signature:
                    try:
                        wallet.remove_key_with_user_password(NRA_WALLET_KEY_USER_SIGNATURE)
                    except Exception:
                        pass
                    wallet.add_key_with_user_password(
                        NRA_WALLET_KEY_USER_SIGNATURE, "certificate", self.user_signature
                    )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("NRA API Credentials"),
                "message": _(
                    "Credentials saved securely in your crypto wallet."
                ),
                "type": "success",
                "sticky": False,
            },
        }
