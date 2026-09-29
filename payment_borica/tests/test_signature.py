# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import re

from odoo.tests import tagged

from ..const import SALE_RESPONSE_SIGN_FIELDS, SALE_SIGN_FIELDS
from .common import BoricaCommon


@tagged("post_install", "-at_install")
class TestBoricaSignature(BoricaCommon):
    def test_canonicalize_length_prefix_and_dash(self):
        # Всяко поле е „дължина в байтове + стойност“; липсващото е само „-“
        data = self.borica._borica_canonicalize(
            {"TERMINAL": "V1800001", "TRTYPE": "1", "AMOUNT": "9.00", "RFU": None},
            ("TERMINAL", "TRTYPE", "AMOUNT", "CURRENCY", "RFU"),
        )
        self.assertEqual(data, b"8V180000111" + b"49.00" + b"-" + b"-")

    def test_canonicalize_counts_utf8_bytes_not_characters(self):
        data = self.borica._borica_canonicalize({"DESC": "Ъ"}, ("DESC",))
        self.assertEqual(data, b"2" + "Ъ".encode())

    def test_sign_verify_roundtrip(self):
        values = {
            "TERMINAL": "V1800001",
            "TRTYPE": "1",
            "AMOUNT": "12.50",
            "CURRENCY": "EUR",
            "ORDER": "000042",
            "TIMESTAMP": "20260929120000",
            "NONCE": "0123456789ABCDEF0123456789ABCDEF",
        }
        p_sign = self.borica._borica_sign(values, SALE_SIGN_FIELDS)
        self.assertRegex(p_sign, r"^[0-9A-F]{512}$")
        self.assertTrue(self.borica._borica_verify(values, p_sign, SALE_SIGN_FIELDS))

    def test_verify_rejects_tampered_amount(self):
        values = {"ACTION": "0", "RC": "00", "AMOUNT": "12.50", "ORDER": "000042"}
        p_sign = self.borica._borica_sign(values, SALE_RESPONSE_SIGN_FIELDS)
        values["AMOUNT"] = "0.01"
        self.assertFalse(
            self.borica._borica_verify(values, p_sign, SALE_RESPONSE_SIGN_FIELDS)
        )

    def test_verify_rejects_non_hex_signature(self):
        self.assertFalse(
            self.borica._borica_verify(
                {"ACTION": "0"}, "not-hex", SALE_RESPONSE_SIGN_FIELDS
            )
        )

    def test_nonce_is_32_uppercase_hex(self):
        nonce = self.borica._borica_nonce()
        self.assertTrue(re.fullmatch(r"[0-9A-F]{32}", nonce))
