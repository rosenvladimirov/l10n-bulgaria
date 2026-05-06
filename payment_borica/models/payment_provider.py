# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import binascii
import logging
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

API_URL_TEST = "https://3dsgate-dev.borica.bg/cgi-bin/cgi_link"
API_URL_PROD = "https://3dsgate.borica.bg/cgi-bin/cgi_link"

# Order MUST match the spec for MAC_GENERAL signing of TRTYPE=1 (Sale).
# Reference: P-OM-41 v4.0 §5.7, page 32.
SALE_SIGN_FIELDS = (
    "TERMINAL",
    "TRTYPE",
    "AMOUNT",
    "CURRENCY",
    "ORDER",
    "TIMESTAMP",
    "NONCE",
    "RFU",
)

SALE_RESPONSE_SIGN_FIELDS = (
    "ACTION",
    "RC",
    "APPROVAL",
    "TERMINAL",
    "TRTYPE",
    "AMOUNT",
    "CURRENCY",
    "ORDER",
    "RRN",
    "INT_REF",
    "PARES_STATUS",
    "ECI",
    "TIMESTAMP",
    "NONCE",
    "RFU",
)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("borica", "Borica APGW")],
        ondelete={"borica": "set default"},
    )

    borica_terminal = fields.Char(
        string="Borica Terminal (TID)",
        help="8-char terminal identifier issued by the acquirer bank, e.g. V1800001.",
        size=8,
    )
    borica_merchant = fields.Char(
        string="Borica Merchant ID",
        help="10-char merchant identifier issued by the acquirer bank.",
        size=10,
    )
    borica_merch_name = fields.Char(
        string="Merchant Name",
        help="Latin merchant name as registered with the acquirer.",
    )
    borica_merch_url = fields.Char(string="Merchant URL")
    borica_email = fields.Char(string="Merchant Email")
    borica_country = fields.Char(string="Country", default="BG", size=2)
    borica_merch_gmt = fields.Char(string="GMT offset", default="+02", size=3)
    borica_lang = fields.Char(string="Default language", default="EN", size=2)
    borica_private_key = fields.Text(
        string="Merchant Private Key (PEM)",
        help="PEM-encoded RSA private key used to sign requests.",
        groups="base.group_system",
    )
    borica_public_cert = fields.Text(
        string="Borica Public Certificate (PEM)",
        help="PEM-encoded Borica certificate used to verify response signatures.",
        groups="base.group_system",
    )

    @api.constrains("state", "code", "borica_terminal", "borica_merchant",
                    "borica_private_key", "borica_public_cert")
    def _check_borica_credentials(self):
        for provider in self:
            if provider.code != "borica" or provider.state == "disabled":
                continue
            missing = []
            if not provider.borica_terminal:
                missing.append("Terminal (TID)")
            if not provider.borica_merchant:
                missing.append("Merchant ID")
            if not provider.borica_private_key:
                missing.append("Private Key")
            if not provider.borica_public_cert:
                missing.append("Public Certificate")
            if missing:
                raise ValidationError(
                    _("Borica provider requires: %s") % ", ".join(missing)
                )

    def _get_default_payment_method_codes(self):
        codes = super()._get_default_payment_method_codes()
        if self.code != "borica":
            return codes
        return ["card", "bancontact"]

    def _borica_get_api_url(self):
        self.ensure_one()
        return API_URL_TEST if self.state == "test" else API_URL_PROD

    @staticmethod
    def _borica_canonicalize(values, field_order):
        """Build the MAC_GENERAL signing string per Borica P-OM-41 v4.0 §5.7.

        For each field in ``field_order``:
          – missing or None → append literal byte ``-`` (0x2D, no length prefix);
          – present → append ``<UTF-8 byte length>`` (decimal, no padding) followed
            by the raw value bytes.

        Returns the bytes ready to be hashed/signed.
        """
        out = bytearray()
        for name in field_order:
            v = values.get(name)
            if v is None or v == "":
                out.extend(b"-")
                continue
            raw = str(v).encode("utf-8")
            out.extend(str(len(raw)).encode("ascii"))
            out.extend(raw)
        return bytes(out)

    def _borica_sign(self, values, field_order=SALE_SIGN_FIELDS):
        """Sign ``values`` with the merchant private key.

        Returns the P_SIGN string — uppercase hex of the RSA-SHA256 PKCS#1 v1.5
        signature (512 hex characters for an RSA-2048 key).
        """
        self.ensure_one()
        if not self.borica_private_key:
            raise ValidationError(_("Borica: private key is not configured"))
        data = self._borica_canonicalize(values, field_order)
        priv = serialization.load_pem_private_key(
            self.borica_private_key.encode("utf-8"), password=None
        )
        signature = priv.sign(data, padding.PKCS1v15(), hashes.SHA256())
        return binascii.hexlify(signature).decode("ascii").upper()

    def _borica_verify(self, values, p_sign_hex, field_order=SALE_RESPONSE_SIGN_FIELDS):
        """Verify a P_SIGN (uppercase hex) using the Borica public certificate."""
        self.ensure_one()
        if not self.borica_public_cert:
            raise ValidationError(_("Borica: public certificate is not configured"))
        data = self._borica_canonicalize(values, field_order)
        cert = load_pem_x509_certificate(self.borica_public_cert.encode("utf-8"))
        try:
            cert.public_key().verify(
                binascii.unhexlify(p_sign_hex),
                data,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except (InvalidSignature, binascii.Error, ValueError):
            return False

    @staticmethod
    def _borica_nonce():
        """32-char uppercase hex nonce (Borica spec mandates exactly 32 chars)."""
        return secrets.token_hex(16).upper()
