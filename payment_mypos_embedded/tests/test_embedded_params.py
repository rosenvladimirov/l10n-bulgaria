# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Server-side embedded-params building. The iFrame itself can only be
validated in a live browser against the myPOS sandbox; here we lock down
the deterministic part — the params blob handed to MyPOSEmbedded.

We reuse payment_mypos's keypair generator so the provider passes its
@api.constrains credential check (the embedded flow doesn't sign, but
the provider record still requires the fields to be enabled).
"""

import json

from odoo.tests.common import TransactionCase

from odoo.addons.payment_mypos.tests.test_signature import _generate_keypair


class TestMyPosEmbeddedParams(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        priv_pem, cert_pem = _generate_keypair()
        cls.provider = cls.env["payment.provider"].create({
            "name": "myPOS Embedded Test",
            "code": "mypos",
            "state": "test",
            "mypos_flow": "embedded",
            "mypos_sid": "000000000000010",
            "mypos_wallet": "61938166610",
            "mypos_key_index": 1,
            "mypos_private_key": priv_pem,
            "mypos_public_cert": cert_pem,
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Embedded Buyer",
            "email": "embedded@example.com",
            "country_id": cls.env.ref("base.bg").id,
        })
        cls.eur = cls.env.ref("base.EUR")
        cls.method_card = cls.env.ref("payment.payment_method_card")

    def _tx(self, reference="MYPOS-EMB-1", amount=42.00):
        return self.env["payment.transaction"].create({
            "provider_id": self.provider.id,
            "payment_method_id": self.method_card.id,
            "reference": reference,
            "amount": amount,
            "currency_id": self.eur.id,
            "partner_id": self.partner.id,
        })

    def test_redirect_form_view_swapped_for_embedded(self):
        view = self.provider._get_redirect_form_view()
        self.assertEqual(
            view, self.env.ref("payment_mypos_embedded.embedded_form"),
            "embedded providers must render the iFrame template, not the "
            "signed auto-submit redirect form",
        )

    def test_redirect_provider_keeps_default_view(self):
        self.provider.mypos_flow = "redirect"
        view = self.provider._get_redirect_form_view()
        self.assertNotEqual(
            view, self.env.ref("payment_mypos_embedded.embedded_form"),
        )

    def test_rendering_values_shape(self):
        tx = self._tx()
        vals = tx._get_specific_rendering_values({})
        self.assertIn("mypos_embedded_params", vals)
        self.assertTrue(vals["mypos_embedded_is_sandbox"])  # state == test
        params = json.loads(vals["mypos_embedded_params"])
        # No signature / private key ever leaves the server in embedded mode.
        self.assertNotIn("signature", {k.lower() for k in params})
        self.assertNotIn("privatekey", {k.lower() for k in params})
        self.assertEqual(params["sid"], "000000000000010")
        self.assertEqual(params["walletNumber"], "61938166610")
        self.assertEqual(params["orderID"], tx.reference)
        self.assertEqual(params["amount"], 42.0)
        self.assertEqual(params["currency"], "EUR")
        self.assertEqual(params["keyIndex"], 1)
        self.assertTrue(params["urlNotify"].endswith("/payment/mypos/notify"))
        self.assertEqual(len(params["cartItems"]), 1)
        self.assertEqual(params["cartItems"][0]["price"], 42.0)

    def test_non_mypos_untouched(self):
        """A non-myPOS provider must fall straight through to super()."""
        # Demo provider ships with core; just assert our override no-ops.
        other = self.env["payment.provider"].search(
            [("code", "!=", "mypos")], limit=1
        )
        if other:
            view = other._get_redirect_form_view()
            self.assertNotEqual(
                view, self.env.ref("payment_mypos_embedded.embedded_form")
            )
