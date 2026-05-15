# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""IPCRefund flow — exercises the shared `_mypos_do_refund` driver plus
the provider build/send/verify helpers, with `requests.post` mocked so no
real myPOS traffic is generated.

The mock signs its response with the SAME test keypair the provider uses,
so the response-signature verification path is exercised end-to-end (this
is the part most likely to regress on a canonicalize change).
"""

import json
from collections import OrderedDict
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from .test_signature import _generate_keypair


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = json.dumps(payload)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class TestMyPosRefundFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        priv_pem, cert_pem = _generate_keypair()
        cls.provider = cls.env["payment.provider"].create({
            "name": "myPOS Test",
            "code": "mypos",
            "state": "test",
            "mypos_sid": "000000000000010",
            "mypos_wallet": "61938166610",
            "mypos_key_index": 1,
            "mypos_private_key": priv_pem,
            "mypos_public_cert": cert_pem,
            "mypos_application_id": "mps-app-30032205",
            "mypos_partner_id": "mps-p-10006566",
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Refund Buyer",
            "email": "refund@example.com",
            "country_id": cls.env.ref("base.bg").id,
        })
        cls.eur = cls.env.ref("base.EUR")
        cls.method_card = cls.env.ref("payment.payment_method_card")

    def _source_tx(self, reference="MYPOS-SRC-1", amount=20.00, trnref="ORIG-TRNREF-1"):
        tx = self.env["payment.transaction"].create({
            "provider_id": self.provider.id,
            "payment_method_id": self.method_card.id,
            "reference": reference,
            "amount": amount,
            "currency_id": self.eur.id,
            "partner_id": self.partner.id,
        })
        tx._set_done()
        tx.provider_reference = trnref
        return tx

    def _signed_gateway_response(self, fields):
        """Build a gateway-style JSON response signed with the test key."""
        ordered = OrderedDict(fields)
        sig = self.provider._mypos_sign(ordered)
        out = OrderedDict(ordered)
        out["Signature"] = sig
        return out

    # --- Payload construction --------------------------------------------

    def test_refund_payload_requires_provider_reference(self):
        """AUP: cannot refund a tx that the gateway never confirmed."""
        src = self.env["payment.transaction"].create({
            "provider_id": self.provider.id,
            "payment_method_id": self.method_card.id,
            "reference": "MYPOS-NOREF",
            "amount": 10.0,
            "currency_id": self.eur.id,
            "partner_id": self.partner.id,
        })  # no _set_done / no provider_reference
        refund = src._create_child_transaction(10.0, is_refund=True)
        with self.assertRaises(ValidationError):
            self.provider._mypos_build_refund_payload(refund, src)

    def test_refund_payload_requires_app_and_partner_id(self):
        self.provider.write({"mypos_application_id": False})
        src = self._source_tx(reference="MYPOS-SRC-NOAPP")
        refund = src._create_child_transaction(5.0, is_refund=True)
        with self.assertRaises(ValidationError):
            self.provider._mypos_build_refund_payload(refund, src)

    def test_refund_payload_field_order_and_trnref(self):
        src = self._source_tx(reference="MYPOS-SRC-ORDER", trnref="TRN-ABC")
        refund = src._create_child_transaction(7.5, is_refund=True)
        payload = self.provider._mypos_build_refund_payload(refund, src)
        keys = list(payload.keys())
        self.assertEqual(keys[0], "IPCmethod")
        self.assertEqual(payload["IPCmethod"], "IPCRefund")
        self.assertEqual(payload["IPC_Trnref"], "TRN-ABC")
        self.assertEqual(payload["Amount"], "7.50")
        self.assertEqual(payload["OutputFormat"], "json")
        self.assertEqual(payload["ApplicationID"], "mps-app-30032205")

    # --- Full driver, HTTP mocked ----------------------------------------

    def test_refund_success_sets_done_and_captures_trnref(self):
        src = self._source_tx(reference="MYPOS-SRC-OK", trnref="ORIG-OK")
        refund = src._create_child_transaction(20.0, is_refund=True)
        resp = self._signed_gateway_response(OrderedDict([
            ("IPCmethod", "IPCRefund"),
            ("Status", "0"),
            ("Amount", "20.00"),
            ("Currency", "EUR"),
            ("IPC_Trnref", "REFUND-TRNREF-99"),
        ]))
        with patch(
            "odoo.addons.payment_mypos.models.payment_provider.requests.post",
            return_value=_FakeResponse(resp),
        ):
            src._mypos_do_refund(source_tx=src, refund_tx=refund)
        self.assertEqual(refund.state, "done")
        self.assertEqual(refund.provider_reference, "REFUND-TRNREF-99")

    def test_refund_declined_sets_error_with_label(self):
        src = self._source_tx(reference="MYPOS-SRC-DECL", trnref="ORIG-DECL")
        refund = src._create_child_transaction(20.0, is_refund=True)
        resp = self._signed_gateway_response(OrderedDict([
            ("IPCmethod", "IPCRefund"),
            ("Status", "13"),  # NOT_SUFFICIENT_FUNDS
            ("Amount", "20.00"),
            ("Currency", "EUR"),
            ("IPC_Trnref", "REFUND-X"),
        ]))
        with patch(
            "odoo.addons.payment_mypos.models.payment_provider.requests.post",
            return_value=_FakeResponse(resp),
        ):
            src._mypos_do_refund(source_tx=src, refund_tx=refund)
        self.assertEqual(refund.state, "error")
        self.assertIn("not_sufficient_funds", (refund.state_message or "").lower())

    def test_refund_response_bad_signature_rejected(self):
        src = self._source_tx(reference="MYPOS-SRC-BADSIG", trnref="ORIG-BADSIG")
        refund = src._create_child_transaction(20.0, is_refund=True)
        # Sign a DIFFERENT payload than what we return → signature won't match
        good = self._signed_gateway_response(OrderedDict([
            ("IPCmethod", "IPCRefund"), ("Status", "0"), ("Amount", "20.00"),
            ("Currency", "EUR"), ("IPC_Trnref", "R1"),
        ]))
        tampered = OrderedDict(good)
        tampered["Amount"] = "999.00"  # mutate AFTER signing
        with patch(
            "odoo.addons.payment_mypos.models.payment_provider.requests.post",
            return_value=_FakeResponse(tampered),
        ):
            src._mypos_do_refund(source_tx=src, refund_tx=refund)
        # Bad signature → driver swallows ValidationError onto refund tx
        self.assertEqual(refund.state, "error")
        self.assertNotEqual(refund.state, "done")
