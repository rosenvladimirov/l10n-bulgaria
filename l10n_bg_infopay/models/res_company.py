# Copyright 2025-2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

INFOPAY_WALLET_UNIQUE_ID_KEY = "infopay_unique_id"
INFOPAY_WALLET_ACCESS_TOKEN_KEY = "infopay_access_token"
INFOPAY_WALLET_ADMIN_UNIQUE_ID_KEY = "infopay_admin_unique_id"
INFOPAY_WALLET_ADMIN_ACCESS_TOKEN_KEY = "infopay_admin_access_token"


class ResCompany(models.Model):
    _inherit = "res.company"

    # Both user-side and admin-side InfoPay credentials live in the
    # registered owner's crypto wallet (l10n_bg_bank_wallet).  The wallet
    # is unlocked with the owner's bcrypt password hash via the wallet
    # module's *_with_user_password helpers — no plaintext session
    # password is needed, so cron can sudo to the owner and still read.
    #
    # The four wallet keys live under separate names so user-side and
    # admin-side credentials cannot collide.  Operators are expected to
    # register a SEPARATE InfoPay ERP for the admin pair (read-only
    # scope) so a leaked admin token cannot initiate payments.

    l10n_bg_infopay_token_user_id = fields.Many2one(
        "res.users",
        string="InfoPay Token Owner",
        help="User whose crypto wallet stores the InfoPay credentials "
             "(both user-side and admin-side).  Pointing at the owner "
             "is non-secret — the credential pairs only decrypt with "
             "the owner's bcrypt password hash.",
    )

    # ── user-side credential management ──────────────────────────────

    def _infopay_set_credentials(self, unique_id, access_token):
        """Store InfoPay user-side credentials in the owner's wallet."""
        self.ensure_one()
        self._infopay_store_wallet_pair(
            INFOPAY_WALLET_UNIQUE_ID_KEY,
            INFOPAY_WALLET_ACCESS_TOKEN_KEY,
            unique_id, access_token,
            label="user",
        )

    def _infopay_get_unique_id(self):
        return self._infopay_read_wallet_key(
            INFOPAY_WALLET_UNIQUE_ID_KEY, label="uniqueId",
        )

    def _infopay_get_access_token(self):
        return self._infopay_read_wallet_key(
            INFOPAY_WALLET_ACCESS_TOKEN_KEY, label="accessToken",
        )

    def _infopay_has_credentials(self):
        """Cheap check that user-side credentials look populated.
        Verifies the owner pointer plus both wallet keys exist; does
        not decrypt.
        """
        self.ensure_one()
        return self._infopay_wallet_pair_present(
            INFOPAY_WALLET_UNIQUE_ID_KEY,
            INFOPAY_WALLET_ACCESS_TOKEN_KEY,
        )

    # ── admin-side credential management ─────────────────────────────

    def _l10n_bg_infopay_set_admin_credentials(self, unique_id, access_token):
        """Store admin (cron/read-only) InfoPay credentials.

        Stored in the same owner wallet as the user-side pair but under
        separate keys, so cron jobs sudo'd to the owner can read them
        without colliding with user-side credentials.  Use a SEPARATE
        ERP registration in the InfoPay portal for the admin pair
        (read-only scope) — never reuse user-side creds.
        """
        self.ensure_one()
        self._infopay_store_wallet_pair(
            INFOPAY_WALLET_ADMIN_UNIQUE_ID_KEY,
            INFOPAY_WALLET_ADMIN_ACCESS_TOKEN_KEY,
            unique_id, access_token,
            label="admin",
        )

    def _l10n_bg_infopay_get_admin_unique_id(self):
        return self._infopay_read_wallet_key(
            INFOPAY_WALLET_ADMIN_UNIQUE_ID_KEY, label="admin uniqueId",
        )

    def _l10n_bg_infopay_get_admin_token(self):
        return self._infopay_read_wallet_key(
            INFOPAY_WALLET_ADMIN_ACCESS_TOKEN_KEY, label="admin accessToken",
        )

    def _l10n_bg_infopay_has_admin_credentials(self):
        self.ensure_one()
        return self._infopay_wallet_pair_present(
            INFOPAY_WALLET_ADMIN_UNIQUE_ID_KEY,
            INFOPAY_WALLET_ADMIN_ACCESS_TOKEN_KEY,
        )

    # ── shared wallet helpers ────────────────────────────────────────

    def _infopay_store_wallet_pair(
        self, uid_key, tok_key, unique_id, access_token, label,
    ):
        """Write a (uniqueId, accessToken) pair into the owner's wallet
        under the two provided key names.  Records the current user as
        owner if no owner is set yet.
        """
        if not unique_id or not access_token:
            raise UserError(self.env._(
                "Both uniqueId and accessToken are required.",
            ))
        if not self.l10n_bg_infopay_token_user_id:
            self.l10n_bg_infopay_token_user_id = self.env.user
        owner = self.l10n_bg_infopay_token_user_id
        Wallet = self.env["crypto.wallet"].sudo()
        wallet = Wallet.get_user_wallet_or_create(user_id=owner.id)
        wallet.add_key_with_user_password(uid_key, "api_key", unique_id)
        wallet.add_key_with_user_password(tok_key, "api_key", access_token)
        _logger.info(
            "Stored InfoPay %s credentials for company %s in wallet of %s.",
            label, self.name, owner.login,
        )

    def _infopay_read_wallet_key(self, key_name, label):
        """Try current user's wallet first; fall back to the registered
        token owner via sudo.  ``label`` only colours error messages.
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"].sudo()

        user_wallet = Wallet.search([
            ("user_id", "=", self.env.user.id),
            ("name", "=", "System Keys"),
        ], limit=1)
        if user_wallet:
            try:
                return user_wallet.get_key_with_user_password(key_name)["data"]
            except Exception:
                pass

        token_user = self.l10n_bg_infopay_token_user_id
        if not token_user:
            raise UserError(self.env._(
                "No InfoPay token owner configured on company '%s'.  "
                "Run _infopay_set_credentials() or "
                "_l10n_bg_infopay_set_admin_credentials() to populate.",
                self.name,
            ))
        owner_wallet = Wallet.sudo().search([
            ("user_id", "=", token_user.id),
            ("name", "=", "System Keys"),
        ], limit=1)
        if not owner_wallet:
            raise UserError(self.env._(
                "Crypto wallet not found for user '%s'.", token_user.name,
            ))
        try:
            return owner_wallet.get_key_with_user_password(key_name)["data"]
        except KeyError as exc:
            raise UserError(self.env._(
                "InfoPay %s missing from owner's wallet — re-run the "
                "matching set-credentials helper to populate.", label,
            )) from exc

    def _infopay_wallet_pair_present(self, uid_key, tok_key):
        """Cheap (no-decrypt) check that both keys live in the owner's
        wallet.  Returns False if owner is unset, wallet is missing or
        either key is absent.
        """
        if not self.l10n_bg_infopay_token_user_id:
            return False
        owner = self.l10n_bg_infopay_token_user_id
        Wallet = self.env["crypto.wallet"].sudo()
        wallet = Wallet.search([
            ("user_id", "=", owner.id),
            ("name", "=", "System Keys"),
        ], limit=1)
        if not wallet:
            return False
        try:
            keys = wallet.list_keys_with_user_password() or []
        except Exception:
            return False
        names = {k.get("name") for k in keys if isinstance(k, dict)}
        return uid_key in names and tok_key in names
