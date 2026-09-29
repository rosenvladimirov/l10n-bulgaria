# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from odoo.addons.payment.tests.common import PaymentCommon

from ..const import SALE_RESPONSE_SIGN_FIELDS


def generate_keypair():
    """RSA-2048 ключ и самоподписан сертификат към него (PEM).

    В тестовете един и същи ключ играе и търговеца, и Борика: с частния
    подписваме отговорите „от шлюза“, а сертификатът ги проверява.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "borica-test")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return key_pem, cert_pem


class BoricaCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        key_pem, cert_pem = generate_keypair()
        cls.borica = cls._prepare_provider(
            "borica",
            update_values={
                "borica_terminal": "V1800001",
                "borica_merchant": "1600000001",
                "borica_merch_name": "Test Merchant",
                "borica_private_key": key_pem,
                "borica_public_cert": cert_pem,
            },
        )
        cls.provider = cls.borica
        cls.currency = cls.currency_euro
        cls.payment_method_id = cls.env.ref("payment.payment_method_card").id

    def _response(self, tx, **overrides):
        """Подписан отговор на Борика за `tx` (по подразбиране одобрен)."""
        values = {
            "ACTION": "0",
            "RC": "00",
            "APPROVAL": "S12345",
            "TERMINAL": self.borica.borica_terminal,
            "TRTYPE": "1",
            "AMOUNT": f"{tx.amount:.2f}",
            "CURRENCY": tx.currency_id.name,
            "ORDER": tx.borica_order,
            "RRN": "123456789012",
            "INT_REF": "INTREF0123456789",
            "PARES_STATUS": "Y",
            "ECI": "05",
            "TIMESTAMP": "20260929120000",
            "NONCE": "0123456789ABCDEF0123456789ABCDEF",
        }
        values.update(overrides)
        values["P_SIGN"] = self.borica._borica_sign(values, SALE_RESPONSE_SIGN_FIELDS)
        return values
