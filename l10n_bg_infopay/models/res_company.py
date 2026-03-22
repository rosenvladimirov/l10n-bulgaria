# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

INFOPAY_WALLET_KEY = "infopay_access_token"


class ResCompany(models.Model):
    _inherit = "res.company"

    infopay_unique_id = fields.Char(
        string="InfoPay Unique ID",
        help="ERP registration Unique ID from InfoPay.",
    )
    infopay_token_user_id = fields.Many2one(
        "res.users",
        string="InfoPay Token Owner",
        help="User whose crypto wallet stores the InfoPay access token.",
    )

    # ── credential management ─────────────────────────────────────────

    def _infopay_set_credentials(self, unique_id, access_token):
        """Store InfoPay credentials.

        ``unique_id`` is saved on the company record.
        ``access_token`` is encrypted in the current user's crypto wallet.
        """
        self.ensure_one()
        self.infopay_unique_id = unique_id
        self.infopay_token_user_id = self.env.user

        wallet = self.env["crypto.wallet"].get_user_wallet_or_create()
        wallet.add_key_with_user_password(
            INFOPAY_WALLET_KEY, "api_key", access_token
        )
        _logger.info(
            "InfoPay credentials stored for company %s (token in wallet of user %s)",
            self.name, self.env.user.login,
        )

    def _infopay_get_access_token(self):
        """Retrieve the InfoPay access token from the crypto wallet.

        Strategy:
        1. Try the current user's own wallet (post-login, fastest path).
        2. Fall back to the token owner's wallet via sudo (cron, first use).
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]

        # ── 1. Current user's wallet (populated at login) ─────────────
        user_wallet = Wallet.search(
            [
                ("user_id", "=", self.env.user.id),
                ("name", "=", "System Keys"),
            ],
            limit=1,
        )
        if user_wallet:
            try:
                key_data = user_wallet.get_key_with_user_password(
                    INFOPAY_WALLET_KEY
                )
                return key_data["data"]
            except Exception:
                pass  # Not in this wallet — try owner's

        # ── 2. Owner's wallet (sudo fallback for cron) ────────────────
        token_user = self.infopay_token_user_id
        if not token_user:
            raise UserError(
                self.env._(
                    "No InfoPay token owner configured on company '%s'.  "
                    "Call _infopay_set_credentials() first.",
                    self.name,
                )
            )

        owner_wallet = Wallet.sudo().search(
            [
                ("user_id", "=", token_user.id),
                ("name", "=", "System Keys"),
            ],
            limit=1,
        )
        if not owner_wallet:
            raise UserError(
                self.env._(
                    "Crypto wallet not found for user '%s'.",
                    token_user.name,
                )
            )

        key_data = owner_wallet.get_key_with_user_password(
            INFOPAY_WALLET_KEY
        )
        return key_data["data"]
