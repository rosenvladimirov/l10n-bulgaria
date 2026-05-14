# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from collections import OrderedDict

from odoo.tests.common import TransactionCase

from .test_signature import _generate_keypair


class TestMyPosNotificationFlow(TransactionCase):
    """End-to-end notification handling — covers the gap between
    `_mypos_sign` (already tested in test_signature) and the live
    `_process_notification_data` lifecycle on payment.transaction.
    """

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
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Buyer",
            "email": "buyer@example.com",
            "country_id": cls.env.ref("base.bg").id,
        })
        cls.currency_eur = cls.env.ref("base.EUR")

    def _new_tx(self, reference="MYPOS-TEST-1", amount=12.50):
        """Create a draft payment.transaction tied to the test provider."""
        return self.env["payment.transaction"].create({
            "provider_id": self.provider.id,
            "reference": reference,
            "amount": amount,
            "currency_id": self.currency_eur.id,
            "partner_id": self.partner.id,
        })

    def _signed_notification(self, fields):
        """Take an OrderedDict of signed fields and append a valid Signature."""
        sig = self.provider._mypos_sign(fields)
        out = OrderedDict(fields)
        out["Signature"] = sig
        return out

    # --- Happy path --------------------------------------------------------

    def test_notification_success_roundtrip(self):
        """Gateway POSTs signed Status=0 → tx.state advances to done."""
        tx = self._new_tx()
        data = self._signed_notification(OrderedDict([
            ("IPCmethod", "IPCPurchaseNotify"),
            ("OrderID", tx.reference),
            ("Status", "0"),
            ("IPC_Trnref", "MYPOS-TXREF-9999"),
            ("Amount", "12.50"),
            ("Currency", "EUR"),
        ]))
        tx._process_notification_data(data)
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, "MYPOS-TXREF-9999",
            "IPC_Trnref must be captured for downstream refund/void calls")

    # --- Cancel flow regression (Fix #1) -----------------------------------

    def test_notification_cancel_flow_signed(self):
        """Cancel callback signed by gateway (Status=cancel) → tx.state=cancel.

        Guards against the pre-fix bug where the controller mutated
        notification_data with `data['Status'] = 'cancel'` before signature
        verification, which would always fail because Status wasn't in the
        signed envelope.
        """
        tx = self._new_tx(reference="MYPOS-TEST-CANCEL")
        data = self._signed_notification(OrderedDict([
            ("IPCmethod", "IPCPurchaseNotify"),
            ("OrderID", tx.reference),
            ("Status", "cancel"),
        ]))
        tx._process_notification_data(data)
        self.assertEqual(tx.state, "cancel")

    def test_notification_unsigned_status_injection_rejected(self):
        """If the controller (or anyone) injects Status AFTER signing, the
        signature must fail. Models the pre-fix tampering bug as an attack."""
        tx = self._new_tx(reference="MYPOS-TEST-TAMPER")
        signed = self._signed_notification(OrderedDict([
            ("IPCmethod", "IPCPurchaseNotify"),
            ("OrderID", tx.reference),
            # Intentionally NO Status field in the signed envelope
        ]))
        # Now an attacker (or buggy controller) appends Status post-sign:
        signed["Status"] = "0"
        tx._process_notification_data(signed)
        # Must NOT transition to done — signature verification must fail
        self.assertNotEqual(tx.state, "done")

    # --- Idempotency (Fix #3) ---------------------------------------------

    def test_notification_duplicate_transmission_idempotent(self):
        """Status=20 (DUPLICATE_TRANSMISSION) must be a no-op, not an error."""
        tx = self._new_tx(reference="MYPOS-TEST-DUP")
        # First success notify
        ok = self._signed_notification(OrderedDict([
            ("IPCmethod", "IPCPurchaseNotify"),
            ("OrderID", tx.reference),
            ("Status", "0"),
        ]))
        tx._process_notification_data(ok)
        self.assertEqual(tx.state, "done")

        # Gateway retries with DUPLICATE_TRANSMISSION marker
        dup = self._signed_notification(OrderedDict([
            ("IPCmethod", "IPCPurchaseNotify"),
            ("OrderID", tx.reference),
            ("Status", "20"),
        ]))
        tx._process_notification_data(dup)
        # State must remain "done", not flipped to "error"
        self.assertEqual(tx.state, "done")

    # --- Status code map (Fix #5) -----------------------------------------

    def test_notification_failed_status_includes_human_label(self):
        """Status 9 (WRONG_AMOUNT) → human-readable error message, not 'unknown'."""
        tx = self._new_tx(reference="MYPOS-TEST-FAIL")
        data = self._signed_notification(OrderedDict([
            ("IPCmethod", "IPCPurchaseNotify"),
            ("OrderID", tx.reference),
            ("Status", "9"),
        ]))
        tx._process_notification_data(data)
        self.assertEqual(tx.state, "error")
        # The state_message must contain the mapped label so support staff
        # can diagnose without consulting myPOS docs each time.
        self.assertIn("wrong_amount", (tx.state_message or "").lower())

    # --- IPC_Trnref capture (Fix #4) --------------------------------------

    def test_notification_captures_ipc_trnref_only_once(self):
        """provider_reference must not be overwritten on subsequent notifies."""
        tx = self._new_tx(reference="MYPOS-TEST-REF")
        first = self._signed_notification(OrderedDict([
            ("IPCmethod", "IPCPurchaseNotify"),
            ("OrderID", tx.reference),
            ("Status", "0"),
            ("IPC_Trnref", "FIRST-TXREF"),
        ]))
        tx._process_notification_data(first)
        self.assertEqual(tx.provider_reference, "FIRST-TXREF")

        # A retry with a different trnref (shouldn't happen in practice, but
        # we test the invariant) must not silently overwrite the original.
        second = self._signed_notification(OrderedDict([
            ("IPCmethod", "IPCPurchaseNotify"),
            ("OrderID", tx.reference),
            ("Status", "20"),
            ("IPC_Trnref", "DIFFERENT-TXREF"),
        ]))
        tx._process_notification_data(second)
        self.assertEqual(tx.provider_reference, "FIRST-TXREF")
