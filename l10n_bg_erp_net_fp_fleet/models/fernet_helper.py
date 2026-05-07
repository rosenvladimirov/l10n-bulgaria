# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Symmetric encryption helper for at-rest secrets (proxy admin tokens).

The encryption key is stored in ``ir.config_parameter`` under
``l10n_bg_erp_net_fp_fleet.fernet_key``. The model below auto-creates
a fresh 32-byte URL-safe key on first use; afterwards it must be
backed up by the operator (rotating it makes existing ciphertexts
unreadable, requiring proxies to re-pair).

Why Fernet over plain plaintext + ACL: the admin_token grants root-
equivalent access to the proxy (it can run arbitrary `compose up
--force-recreate` and read fiscal-receipt logs). Storing it in
plaintext means anyone with read on the table — including a database
backup leak — has fleet root. Fernet (AES-128-CBC + HMAC-SHA256 +
versioning) is the conservative default; it's cheap to add and the
threat model already includes "DB backup ends up on a wrong S3".
"""
from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)

_KEY_PARAM = "l10n_bg_erp_net_fp_fleet.fernet_key"


class FernetHelper(models.AbstractModel):
    _name = "erpnet.fp.fernet"
    _description = "Fernet helper for ErpNet.FP fleet"

    # ─── Key management ─────────────────────────────────────────

    def _ensure_key(self) -> bytes:
        """Return the active Fernet key as bytes, generating one if missing.

        Reads with ``sudo()`` because the param is restricted to
        ``base.group_system`` via security XML (kept out of normal
        user reach).
        """
        from cryptography.fernet import Fernet

        ICP = self.env["ir.config_parameter"].sudo()
        raw = (ICP.get_param(_KEY_PARAM) or "").strip()
        if raw:
            return raw.encode("ascii")
        new = Fernet.generate_key()
        ICP.set_param(_KEY_PARAM, new.decode("ascii"))
        _logger.info(
            "Generated new Fernet key for fleet admin tokens "
            "(ir.config_parameter=%s). BACK THIS UP — losing it forces "
            "all proxies to re-pair.", _KEY_PARAM,
        )
        return new

    # ─── Encrypt / decrypt ──────────────────────────────────────

    def encrypt(self, plaintext: str) -> str:
        """Return base64-encoded Fernet ciphertext, or '' if plaintext is empty."""
        if not plaintext:
            return ""
        from cryptography.fernet import Fernet

        f = Fernet(self._ensure_key())
        return f.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a Fernet token. Returns '' if input is empty or
        decryption fails (key rotation, tampered DB row).
        """
        if not ciphertext:
            return ""
        from cryptography.fernet import Fernet, InvalidToken

        try:
            f = Fernet(self._ensure_key())
            return f.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            _logger.warning(
                "Fernet decrypt failed (key rotated or DB row tampered): %s",
                exc,
            )
            return ""
