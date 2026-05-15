# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Embedded flow: emit MyPOSEmbedded.createPayment params (no
        signature). For redirect flow defer to payment_mypos's logic.

        The Embedded SDK never sees a private key — the only secret in
        the loop is the RSA pair on the server, used solely to verify
        the signed urlNotify S2S callback (handled by payment_mypos's
        existing /payment/mypos/notify controller + _mypos_verify).
        """
        res = super()._get_specific_rendering_values(processing_values)
        provider = self.provider_id
        if provider.code != "mypos" or provider.mypos_flow != "embedded":
            return res

        # cartItems: a single synthetic line keeps the iFrame happy without
        # leaking SO line detail; the amount is authoritative anyway.
        cart_items = [
            {
                "article": (self.reference or "Order")[:128],
                "quantity": 1,
                "price": float(self.amount),
                "currency": self.currency_id.name,
            }
        ]
        params = {
            "sid": provider.mypos_sid or "",
            "walletNumber": provider.mypos_wallet or "",
            "amount": float(self.amount),
            "currency": self.currency_id.name,
            "orderID": self.reference,
            "keyIndex": provider.mypos_key_index or 1,
            "urlOk": self._mypos_get_return_url("ok"),
            "urlCancel": self._mypos_get_return_url("cancel"),
            "urlNotify": self._mypos_get_return_url("notify"),
            "cartItems": cart_items,
        }
        return {
            "mypos_embedded_params": json.dumps(params),
            "mypos_embedded_is_sandbox": provider.state == "test",
            "mypos_embedded_mount_id": "myPOSEmbeddedCheckout_%s" % self.id,
        }
