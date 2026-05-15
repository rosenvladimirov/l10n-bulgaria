# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

API_URL_TEST = "https://www.mypos.com/vmp/checkout-test"
API_URL_PROD = "https://www.mypos.com/vmp/checkout"


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("mypos", "myPOS")],
        ondelete={"mypos": "set default"},
    )

    mypos_sid = fields.Char(
        string="myPOS Store ID (SID)",
        help="Store ID provided by myPOS. Sandbox default: 000000000000010",
    )
    mypos_wallet = fields.Char(
        string="myPOS Wallet Number",
        help="Wallet number associated with the merchant. Sandbox default: 61938166610",
    )
    mypos_key_index = fields.Integer(
        string="Key Index",
        default=1,
        help="Index of the RSA key pair registered in myPOS.",
    )
    mypos_private_key = fields.Text(
        string="Merchant Private Key (RSA, PEM)",
        help="PEM-encoded RSA private key used to sign requests.",
        groups="base.group_system",
    )
    mypos_public_cert = fields.Text(
        string="myPOS Public Certificate (PEM)",
        help="PEM-encoded myPOS certificate used to verify response signatures.",
        groups="base.group_system",
    )

    @api.constrains("state", "code", "mypos_sid", "mypos_wallet", "mypos_private_key", "mypos_public_cert")
    def _check_mypos_credentials(self):
        for provider in self:
            if provider.code != "mypos" or provider.state == "disabled":
                continue
            missing = []
            if not provider.mypos_sid:
                missing.append("Store ID")
            if not provider.mypos_wallet:
                missing.append("Wallet")
            if not provider.mypos_private_key:
                missing.append("Private Key")
            if not provider.mypos_public_cert:
                missing.append("Public Certificate")
            if missing:
                raise ValidationError(
                    _("myPOS provider requires: %s") % ", ".join(missing)
                )

    def _get_default_payment_method_codes(self):
        codes = super()._get_default_payment_method_codes()
        if self.code != "mypos":
            return codes
        return ["mypos"]

    def _mypos_get_api_url(self):
        self.ensure_one()
        return API_URL_TEST if self.state == "test" else API_URL_PROD

    @staticmethod
    def _mypos_canonicalize(params):
        """Concatenate ordered param values with '-' then base64-encode.

        Replicates `base64_encode(implode('-', params))` from the official
        myPOS PHP SDK (IPC/Base.php::_createSignature).
        """
        joined = "-".join("" if v is None else str(v) for v in params.values())
        return base64.b64encode(joined.encode("utf-8"))

    def _mypos_sign(self, params):
        """Sign ``params`` (an ordered dict) with the merchant private key.

        Returns a base64-encoded RSA-SHA256 signature in PKCS#1 v1.5 padding.
        """
        self.ensure_one()
        if not self.mypos_private_key:
            raise ValidationError(_("myPOS: merchant private key is not configured"))
        data = self._mypos_canonicalize(params)
        priv = serialization.load_pem_private_key(
            self.mypos_private_key.encode("utf-8"), password=None
        )
        signature = priv.sign(data, padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode("ascii")

    def _mypos_verify(self, params, signature_b64):
        """Verify a base64 RSA-SHA256 signature using the myPOS public cert."""
        self.ensure_one()
        if not self.mypos_public_cert:
            raise ValidationError(_("myPOS: public certificate is not configured"))
        data = self._mypos_canonicalize(params)
        cert = load_pem_x509_certificate(self.mypos_public_cert.encode("utf-8"))
        pub = cert.public_key()
        try:
            pub.verify(
                base64.b64decode(signature_b64),
                data,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False

    # ──────────────────────────────────────────────────────────────────
    # Partner-level API credentials (clientId / clientSecret)
    # ──────────────────────────────────────────────────────────────────
    # Stored in the company-owner's `crypto.wallet`, NOT on this model.
    # Rationale (mirrors l10n_bg_infopay 6.0.0 pattern):
    #   • Owner-bound encryption — wallet is unlocked with the owner's
    #     bcrypt password hash, so cron jobs sudo-ing to the owner can
    #     read them without prompting for a session password.
    #   • Per-company isolation — wallet is keyed by user_id, and we look
    #     up the owner via `company.partner_id.user_ids[:1]`.
    #   • No plaintext footprint on payment.provider — secrets never
    #     appear in record dumps, exports, or backup CSVs.
    # The myPOS Checkout API hosted-redirect flow (IPCPurchase) still uses
    # SID + WalletNumber + RSA private key from the existing fields; the
    # clientId/Secret pair is for partner-side endpoints (provisioning,
    # IPN management) introduced in v1.4.1.

    _WALLET_KEY_CLIENT_ID = "mypos_client_id"
    _WALLET_KEY_CLIENT_SECRET = "mypos_client_secret"

    def _mypos_wallet_owner_id(self):
        """Pick the user_id that owns the wallet holding myPOS credentials.

        Matches the InfoPay convention: the first user linked to the
        company partner. Falls back to current user if no owner exists yet
        (e.g. fresh sandbox install) — sudo callers will still work.
        """
        self.ensure_one()
        users = self.company_id.partner_id.user_ids
        return users[:1].id or self.env.user.id

    def _mypos_get_client_credentials(self):
        """Return (clientId, clientSecret) from the owner's crypto.wallet.

        Returns (None, None) if either is missing — callers decide whether
        that's a hard error or expected (e.g. before first credential gen).
        """
        self.ensure_one()
        Wallet = self.env["crypto.wallet"].sudo()
        owner_id = self._mypos_wallet_owner_id()
        try:
            cid = Wallet.quick_access(self._WALLET_KEY_CLIENT_ID, user_id=owner_id)
            sec = Wallet.quick_access(self._WALLET_KEY_CLIENT_SECRET, user_id=owner_id)
        except Exception as e:
            _logger.warning("myPOS: wallet read failed for company %s: %s", self.company_id.id, e)
            return None, None
        return cid, sec

    def _mypos_set_client_credentials(self, client_id, client_secret):
        """Persist (clientId, clientSecret) into the owner's crypto.wallet.

        Idempotent — calling again with new values rotates the keys.
        Raises ValidationError if either argument is empty; the wallet
        layer additionally requires write permissions (group_system).
        """
        self.ensure_one()
        if not client_id or not client_secret:
            raise ValidationError(_("myPOS: both clientId and clientSecret are required"))
        Wallet = self.env["crypto.wallet"].sudo()
        owner_id = self._mypos_wallet_owner_id()
        Wallet.quick_store(self._WALLET_KEY_CLIENT_ID, "text", client_id, user_id=owner_id)
        Wallet.quick_store(self._WALLET_KEY_CLIENT_SECRET, "text", client_secret, user_id=owner_id)
        _logger.info(
            "myPOS: client credentials stored in wallet for company %s (owner uid=%s)",
            self.company_id.id, owner_id,
        )
        return True

    def _mypos_has_client_credentials(self):
        """Cheap presence check — True iff both wallet keys decrypt."""
        cid, sec = self._mypos_get_client_credentials()
        return bool(cid and sec)
