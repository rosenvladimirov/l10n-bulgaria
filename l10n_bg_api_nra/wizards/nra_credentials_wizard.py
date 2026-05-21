import base64
import logging
import re

from odoo import _, api, fields, models
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

    # --- Certificate upload (.p12/.pfx) ---
    certificate_file = fields.Binary(
        string="Certificate File (.p12/.pfx)",
        help="Upload your Qualified Electronic Signature (QES) file. "
             "The PIN and public certificate will be extracted automatically.",
    )
    certificate_filename = fields.Char(
        string="Certificate Filename",
    )
    certificate_password = fields.Char(
        string="Certificate Password (PIN)",
        help="Password / PIN for the .p12/.pfx file.",
    )

    # --- Extracted / manual fields ---
    user_pin = fields.Char(
        string="User PIN",
        help="Personal identifier (PIN/FN) of the person authorized "
             "to submit declarations. Auto-filled from certificate if uploaded.",
    )
    user_signature = fields.Text(
        string="User Certificate (QES Base64)",
        help="Base64-encoded DER public certificate. "
             "Auto-filled from .p12 upload.",
    )

    @api.onchange("certificate_file", "certificate_password")
    def _onchange_certificate_file(self):
        """Extract ЕГН and public certificate from uploaded .p12/.pfx file."""
        if not self.certificate_file:
            return
        if not self.certificate_password:
            return

        try:
            egn, cert_b64 = self._extract_p12_data(
                base64.b64decode(self.certificate_file),
                self.certificate_password.encode("utf-8"),
            )
        except UserError:
            raise
        except Exception as exc:
            raise UserError(
                _("Failed to read certificate: %s", exc)
            ) from exc

        if egn:
            self.user_pin = egn
        if cert_b64:
            self.user_signature = cert_b64

    def _extract_p12_data(self, p12_bytes, password):
        """Extract ЕГН and Base64 DER certificate from PKCS#12 data.

        :param p12_bytes: raw .p12/.pfx file bytes
        :param password: password bytes
        :returns: tuple (egn_str, cert_base64_str)
        """
        from cryptography.hazmat.primitives.serialization import pkcs12, Encoding

        private_key, certificate, chain = pkcs12.load_key_and_certificates(
            p12_bytes, password
        )

        if not certificate:
            raise UserError(_("No certificate found in the .p12 file."))

        # Extract ЕГН from subject — Bulgarian КЕП stores it in
        # serialNumber OID (2.5.4.5) or in the Subject CN
        egn = None
        from cryptography.x509.oid import NameOID
        for attr in certificate.subject:
            if attr.oid == NameOID.SERIAL_NUMBER:
                # serialNumber often contains "PNOBG-XXXXXXXXXX"
                val = attr.value
                match = re.search(r"\d{10}", val)
                if match:
                    egn = match.group(0)
                break

        # DER-encode the certificate and Base64 it
        der_bytes = certificate.public_bytes(Encoding.DER)
        cert_b64 = base64.b64encode(der_bytes).decode("ascii")

        _logger.info(
            "Extracted certificate: subject=%s, EGN=%s, cert_size=%d",
            certificate.subject,
            egn[:3] + "..." if egn else None,
            len(der_bytes),
        )
        return egn, cert_b64

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
                real_uid = self.env.user.id  # capture before sudo
                Wallet = self.env["crypto.wallet"].sudo()
                wallet = Wallet.get_user_wallet_or_create(user_id=real_uid)
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
                    "Credentials saved in your crypto wallet "
                    "and system parameters."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_test_connection(self):
        """Delegate to company's test connection action."""
        self.ensure_one()
        return self.company_id.action_nra_test_connection()

    def action_clear_token(self):
        """Delegate to company's clear token action."""
        self.ensure_one()
        return self.company_id.action_nra_clear_token()
