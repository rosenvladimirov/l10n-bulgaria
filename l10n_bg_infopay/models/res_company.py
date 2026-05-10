# Copyright 2025-2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
import logging

from cryptography.fernet import Fernet, InvalidToken

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

INFOPAY_WALLET_KEY = "infopay_access_token"
INFOPAY_ADMIN_FERNET_KEY_PARAM = "l10n_bg_infopay.admin_fernet_key"


class ResCompany(models.Model):
    _inherit = "res.company"

    # ── User-side credentials (interactive, password-protected) ───────
    # Used for manual import + payment-order initiation: the operator's
    # session password decrypts the wallet on demand.

    l10n_bg_infopay_unique_id = fields.Char(
        string="InfoPay Unique ID",
        help="ERP registration Unique ID from InfoPay (read+write scope, "
             "interactive operator use).",
    )
    l10n_bg_infopay_token_user_id = fields.Many2one(
        "res.users",
        string="InfoPay Token Owner",
        help="User whose crypto wallet stores the InfoPay access token.",
    )

    # ── Admin-side credentials (cron, read-only, no password) ─────────
    # Stored as Fernet-encrypted ciphertext in a Char on the company
    # record; the symmetric key lives in ir.config_parameter (group_system
    # only).  Same pattern as l10n_bg_erp_net_fp_fleet.admin_token.
    # Use a SEPARATE InfoPay ERP registration with read-only scope for
    # this — never the same uniqueId/token as the user-side credentials.

    l10n_bg_infopay_admin_unique_id = fields.Char(
        string="InfoPay Admin Unique ID",
        help="ERP registration Unique ID for the read-only / cron-only "
             "InfoPay token.  Use a SEPARATE registration in the InfoPay "
             "portal — do not reuse the user-side credentials.",
    )
    l10n_bg_infopay_admin_token_encrypted = fields.Char(
        string="InfoPay Admin Token (encrypted)",
        groups="base.group_system",
        help="Fernet ciphertext of the admin access token.  The symmetric "
             "key lives in ir.config_parameter "
             "'l10n_bg_infopay.admin_fernet_key' (auto-generated on first "
             "set, group_system only).",
    )

    # ── credential management ─────────────────────────────────────────

    def _infopay_set_credentials(self, unique_id, access_token):
        """Store InfoPay credentials.

        ``unique_id`` is saved on the company record.
        ``access_token`` is encrypted in the current user's crypto wallet.
        """
        self.ensure_one()
        self.l10n_bg_infopay_unique_id = unique_id
        self.l10n_bg_infopay_token_user_id = self.env.user

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
        token_user = self.l10n_bg_infopay_token_user_id
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

    # ── admin-token Fernet helpers ────────────────────────────────────

    @api.model
    def _l10n_bg_infopay_admin_fernet(self):
        """Return a Fernet handle, generating + persisting a key on
        first use.  Key lives in ir.config_parameter under
        'l10n_bg_infopay.admin_fernet_key' (group_system).

        Race-protected: takes a row-level pg_advisory_xact_lock keyed
        on the param name's hash before checking + inserting, so two
        concurrent workers cannot both generate keys.  Without the
        lock, last-write-wins corrupts the keyspace (any token
        encrypted with the loser key becomes undecryptable).
        """
        ICP = self.env["ir.config_parameter"].sudo()
        # Fast path — key already exists, no need for the lock.
        key_b64 = ICP.get_param(INFOPAY_ADMIN_FERNET_KEY_PARAM)
        if key_b64:
            return Fernet(key_b64.encode())
        # Slow path — acquire advisory lock and re-check (DCL pattern).
        # Hash the param name into the int4 lock key space.
        lock_key = abs(hash(INFOPAY_ADMIN_FERNET_KEY_PARAM)) % (2**31 - 1)
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(%s)", (lock_key,),
        )
        # Re-read inside the lock — another worker may have just won
        # the race and persisted a key.
        key_b64 = ICP.get_param(INFOPAY_ADMIN_FERNET_KEY_PARAM)
        if not key_b64:
            key_b64 = Fernet.generate_key().decode()
            ICP.set_param(INFOPAY_ADMIN_FERNET_KEY_PARAM, key_b64)
            _logger.info(
                "Generated new InfoPay admin Fernet key (param '%s').",
                INFOPAY_ADMIN_FERNET_KEY_PARAM,
            )
        return Fernet(key_b64.encode())

    def _l10n_bg_infopay_set_admin_credentials(self, unique_id, access_token):
        """Store admin (read-only / cron) InfoPay credentials.

        Symmetric encryption with a server-wide Fernet key.  Use a
        SEPARATE ERP registration in the InfoPay portal for this —
        do NOT reuse the user-side credentials, so a leaked admin token
        cannot be used to initiate payments.
        """
        self.ensure_one()
        if not unique_id or not access_token:
            raise UserError(self.env._(
                "Both uniqueId and accessToken are required."
            ))
        f = self._l10n_bg_infopay_admin_fernet()
        ciphertext = f.encrypt(access_token.encode()).decode()
        self.sudo().write({
            "l10n_bg_infopay_admin_unique_id": unique_id,
            "l10n_bg_infopay_admin_token_encrypted": ciphertext,
        })
        _logger.info(
            "Stored InfoPay admin credentials for company %s "
            "(uniqueId=%s).", self.name, unique_id,
        )

    def _l10n_bg_infopay_get_admin_token(self):
        """Decrypt and return the admin access token.  No user password
        required — designed for cron / scheduled jobs.
        """
        self.ensure_one()
        ciphertext = self.sudo().l10n_bg_infopay_admin_token_encrypted
        if not ciphertext:
            raise UserError(self.env._(
                "No InfoPay admin token configured on company '%s'.  "
                "Call _l10n_bg_infopay_set_admin_credentials() first.",
                self.name,
            ))
        f = self._l10n_bg_infopay_admin_fernet()
        try:
            return f.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise UserError(self.env._(
                "InfoPay admin token cannot be decrypted — Fernet key "
                "may have been rotated or the ciphertext corrupted.  "
                "Re-set credentials via "
                "_l10n_bg_infopay_set_admin_credentials()."
            )) from exc

    def _l10n_bg_infopay_has_admin_credentials(self):
        """Cheap check (no decryption) that admin creds are set."""
        self.ensure_one()
        return bool(
            self.l10n_bg_infopay_admin_unique_id
            and self.sudo().l10n_bg_infopay_admin_token_encrypted
        )
