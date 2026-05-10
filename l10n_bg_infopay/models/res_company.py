# Copyright 2025-2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from cryptography.fernet import Fernet, InvalidToken

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

INFOPAY_WALLET_UNIQUE_ID_KEY = "infopay_unique_id"
INFOPAY_WALLET_ACCESS_TOKEN_KEY = "infopay_access_token"
INFOPAY_ADMIN_FERNET_KEY_PARAM = "l10n_bg_infopay.admin_fernet_key"


class ResCompany(models.Model):
    _inherit = "res.company"

    # ── User-side credentials ────────────────────────────────────────
    # Both ``uniqueId`` and ``accessToken`` are paired secrets — neither
    # alone authenticates with InfoPay; they sit on the same security
    # boundary, so they live in the same place: the user's crypto
    # wallet (password-protected).  No part of these credentials lives
    # on the public ``res.company`` record.

    l10n_bg_infopay_token_user_id = fields.Many2one(
        "res.users",
        string="InfoPay Token Owner",
        help="User whose crypto wallet stores the InfoPay credentials "
             "(uniqueId + accessToken).  Pointing at the owner is "
             "non-secret — the credential pair only decrypts with the "
             "owner's session password.",
    )

    # ── Admin-side credentials (cron, no password) ───────────────────
    # Both fields are Fernet ciphertexts.  Symmetric key lives in
    # ir.config_parameter (group_system only).  Use a SEPARATE InfoPay
    # ERP registration with read-only scope for these — never the same
    # uniqueId/token as the user-side credentials.

    l10n_bg_infopay_admin_unique_id_encrypted = fields.Char(
        string="InfoPay Admin uniqueId (encrypted)",
        groups="base.group_system",
        help="Fernet ciphertext of the admin uniqueId.  Sits on the "
             "same security boundary as the admin token; same Fernet "
             "key.",
    )
    l10n_bg_infopay_admin_token_encrypted = fields.Char(
        string="InfoPay Admin Token (encrypted)",
        groups="base.group_system",
        help="Fernet ciphertext of the admin access token.  The "
             "symmetric key lives in ir.config_parameter "
             "'l10n_bg_infopay.admin_fernet_key' (auto-generated on "
             "first set, group_system only).",
    )

    # ── user-side credential management ──────────────────────────────

    def _infopay_set_credentials(self, unique_id, access_token):
        """Store InfoPay user-side credentials.

        Both ``unique_id`` and ``access_token`` are written into the
        current user's crypto wallet under separate keys; the company
        record only remembers *who* the wallet owner is so cron can
        sudo-fall-back to that user's wallet.
        """
        self.ensure_one()
        if not unique_id or not access_token:
            raise UserError(self.env._(
                "Both uniqueId and accessToken are required.",
            ))
        self.l10n_bg_infopay_token_user_id = self.env.user

        wallet = self.env["crypto.wallet"].get_user_wallet_or_create()
        wallet.add_key_with_user_password(
            INFOPAY_WALLET_UNIQUE_ID_KEY, "api_key", unique_id,
        )
        wallet.add_key_with_user_password(
            INFOPAY_WALLET_ACCESS_TOKEN_KEY, "api_key", access_token,
        )
        _logger.info(
            "InfoPay user credentials stored for company %s in wallet "
            "of user %s.", self.name, self.env.user.login,
        )

    def _infopay_get_unique_id(self):
        """Retrieve the InfoPay uniqueId from the wallet."""
        return self._infopay_read_wallet_key(
            INFOPAY_WALLET_UNIQUE_ID_KEY, label="uniqueId",
        )

    def _infopay_get_access_token(self):
        """Retrieve the InfoPay access token from the wallet."""
        return self._infopay_read_wallet_key(
            INFOPAY_WALLET_ACCESS_TOKEN_KEY, label="accessToken",
        )

    def _infopay_read_wallet_key(self, key_name, label):
        """Shared lookup: try current user's wallet first, fall back
        to the registered token owner via sudo (cron / first use).
        ``label`` only colours error messages.
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"]

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
                "Run _infopay_set_credentials() to populate the wallet.",
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
                "InfoPay %s missing from owner's wallet — re-run "
                "_infopay_set_credentials() to populate.", label,
            )) from exc

    def _infopay_has_credentials(self):
        """Cheap check that user-side credentials look populated.
        Does not decrypt — just verifies the owner pointer exists.
        """
        self.ensure_one()
        return bool(self.l10n_bg_infopay_token_user_id)

    # ── admin-token Fernet helpers ────────────────────────────────────

    @api.model
    def _l10n_bg_infopay_admin_fernet(self):
        """Return a Fernet handle, generating + persisting a key on
        first use.  Race-protected via pg_advisory_xact_lock so two
        concurrent workers cannot both regenerate the key.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        key_b64 = ICP.get_param(INFOPAY_ADMIN_FERNET_KEY_PARAM)
        if key_b64:
            return Fernet(key_b64.encode())
        lock_key = abs(hash(INFOPAY_ADMIN_FERNET_KEY_PARAM)) % (2**31 - 1)
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(%s)", (lock_key,),
        )
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

        Both fields are Fernet-encrypted with a server-wide key.  Use
        a SEPARATE ERP registration in the InfoPay portal — do NOT
        reuse the user-side credentials, so a leaked admin pair cannot
        initiate payments.
        """
        self.ensure_one()
        if not unique_id or not access_token:
            raise UserError(self.env._(
                "Both uniqueId and accessToken are required.",
            ))
        f = self._l10n_bg_infopay_admin_fernet()
        self.sudo().write({
            "l10n_bg_infopay_admin_unique_id_encrypted":
                f.encrypt(unique_id.encode()).decode(),
            "l10n_bg_infopay_admin_token_encrypted":
                f.encrypt(access_token.encode()).decode(),
        })
        _logger.info(
            "Stored InfoPay admin credentials for company %s.", self.name,
        )

    def _l10n_bg_infopay_get_admin_unique_id(self):
        return self._l10n_bg_infopay_decrypt_admin(
            "l10n_bg_infopay_admin_unique_id_encrypted", "uniqueId",
        )

    def _l10n_bg_infopay_get_admin_token(self):
        return self._l10n_bg_infopay_decrypt_admin(
            "l10n_bg_infopay_admin_token_encrypted", "accessToken",
        )

    def _l10n_bg_infopay_decrypt_admin(self, field_name, label):
        self.ensure_one()
        ciphertext = self.sudo()[field_name]
        if not ciphertext:
            raise UserError(self.env._(
                "No InfoPay admin %s configured on company '%s'.  "
                "Call _l10n_bg_infopay_set_admin_credentials() first.",
                label, self.name,
            ))
        f = self._l10n_bg_infopay_admin_fernet()
        try:
            return f.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise UserError(self.env._(
                "InfoPay admin %s cannot be decrypted — Fernet key may "
                "have been rotated or the ciphertext corrupted.  "
                "Re-set credentials.", label,
            )) from exc

    def _l10n_bg_infopay_has_admin_credentials(self):
        """Cheap check (no decryption) that admin creds are set."""
        self.ensure_one()
        sudoed = self.sudo()
        return bool(
            sudoed.l10n_bg_infopay_admin_unique_id_encrypted
            and sudoed.l10n_bg_infopay_admin_token_encrypted
        )
