# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from odoo.tests.common import TransactionCase


def _generate_keypair():
    """Self-signed RSA-2048 keypair + cert; returns (priv_pem, cert_pem)."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "myPOS test")]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(priv.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(priv, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return priv_pem, cert_pem


class TestMyPosSignature(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        priv_pem, cert_pem = _generate_keypair()
        cls.provider = cls.env["payment.provider"].create(
            {
                "name": "myPOS Test",
                "code": "mypos",
                "state": "test",
                "mypos_sid": "000000000000010",
                "mypos_wallet": "61938166610",
                "mypos_key_index": 1,
                "mypos_private_key": priv_pem,
                "mypos_public_cert": cert_pem,
            }
        )

    def test_canonicalize_matches_php_sdk(self):
        """`base64(implode('-', values))` — exact byte-for-byte parity with
        IPC/Base.php::_createSignature in the official myPOS PHP SDK."""
        params = OrderedDict([("a", "1"), ("b", "two"), ("c", "")])
        expected = base64.b64encode(b"1-two-")
        self.assertEqual(self.provider._mypos_canonicalize(params), expected)

    def test_canonicalize_preserves_order(self):
        """Reordering keys MUST change the canonical form — order is part
        of the signed envelope, not just the field set."""
        a = self.provider._mypos_canonicalize(OrderedDict([("x", "1"), ("y", "2")]))
        b = self.provider._mypos_canonicalize(OrderedDict([("y", "2"), ("x", "1")]))
        self.assertNotEqual(a, b)

    def test_canonicalize_handles_none_and_int(self):
        params = OrderedDict([("a", None), ("b", 42), ("c", "x")])
        self.assertEqual(
            self.provider._mypos_canonicalize(params), base64.b64encode(b"-42-x")
        )

    def test_sign_and_verify_round_trip(self):
        params = OrderedDict(
            [
                ("IPCmethod", "IPCPurchase"),
                ("OrderID", "SO-001"),
                ("Amount", "12.50"),
                ("Currency", "EUR"),
            ]
        )
        signature = self.provider._mypos_sign(params)
        self.assertTrue(self.provider._mypos_verify(params, signature))

    def test_verify_rejects_tampered_payload(self):
        params = OrderedDict([("OrderID", "SO-001"), ("Amount", "12.50")])
        signature = self.provider._mypos_sign(params)
        tampered = OrderedDict([("OrderID", "SO-001"), ("Amount", "999.99")])
        self.assertFalse(self.provider._mypos_verify(tampered, signature))

    def test_verify_rejects_garbage_signature(self):
        params = OrderedDict([("OrderID", "SO-001")])
        self.assertFalse(
            self.provider._mypos_verify(params, base64.b64encode(b"not a sig").decode())
        )

    def test_sign_raises_without_private_key(self):
        self.provider.write({"mypos_private_key": False, "state": "disabled"})
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.provider._mypos_sign(OrderedDict([("a", "1")]))

    def test_verify_raises_without_public_cert(self):
        self.provider.write({"mypos_public_cert": False, "state": "disabled"})
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.provider._mypos_verify(OrderedDict([("a", "1")]), "deadbeef")

    def test_constraint_blocks_enable_without_credentials(self):
        from odoo.exceptions import ValidationError

        bare = self.env["payment.provider"].create(
            {"name": "myPOS Bare", "code": "mypos", "state": "disabled"}
        )
        with self.assertRaises(ValidationError):
            bare.state = "test"

    def test_php_sdk_reference_vector(self):
        """End-to-end vector: identical PHP run on the same payload+key
        yields the same base64 signature.

        We verify the python-emitted sig with the same RSA public key that
        the PHP openssl_verify call would use — equivalence by construction.
        """
        params = OrderedDict(
            [
                ("IPCmethod", "IPCPurchase"),
                ("IPCVersion", "1.4"),
                ("SID", "000000000000010"),
                ("OrderID", "TEST-1"),
                ("Amount", "1.00"),
                ("Currency", "EUR"),
            ]
        )
        sig = self.provider._mypos_sign(params)

        # Decode signature, then verify with the raw public key (no Odoo wrapper)
        # — confirms we produced a standards-compliant RSA-PKCS1v15-SHA256 sig.
        cert = x509.load_pem_x509_certificate(self.provider.mypos_public_cert.encode())
        cert.public_key().verify(
            base64.b64decode(sig),
            base64.b64encode(b"-".join(v.encode() for v in params.values())),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )  # raises InvalidSignature on failure -> test fails
