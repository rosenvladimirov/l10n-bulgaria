# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


def _hash(otp):
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


class TestOtpFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({
            "email_verification_method": "otp",
            "email_verification_otp_length": 6,
            "email_verification_max_attempts": 3,
            "email_verification_resend_cooldown": 60,
            "email_verification_expiry_minutes": 30,
        })
        cls.user = cls.env["res.users"].create({
            "name": "OTP Test",
            "login": "otp.test@example.com",
            "email_verified": False,
        })

    def test_credentials_generation_does_not_persist_raw_otp(self):
        creds = self.user._generate_verification_credentials()
        self.assertIn("otp", creds)
        self.assertIn("token", creds)
        self.assertEqual(len(creds["otp"]), 6)
        self.assertEqual(
            self.user.email_verification_otp_hash,
            _hash(creds["otp"]),
        )

    def test_correct_otp_clears_state_and_marks_verified(self):
        creds = self.user._generate_verification_credentials()
        self.assertTrue(self.user._verify_email_otp(creds["otp"]))
        self.assertTrue(self.user.email_verified)
        self.assertFalse(self.user.email_verification_otp_hash)
        self.assertFalse(self.user.email_verification_token)
        self.assertFalse(self.user.email_verification_expiry)
        self.assertEqual(self.user.email_verification_attempts, 0)

    def test_wrong_otp_increments_attempts(self):
        self.user._generate_verification_credentials()
        self.assertFalse(self.user._verify_email_otp("000000"))
        self.assertEqual(self.user.email_verification_attempts, 1)
        self.assertFalse(self.user._verify_email_otp("000000"))
        self.assertEqual(self.user.email_verification_attempts, 2)

    def test_max_attempts_locks_account(self):
        # max=3 — three wrong tries should clear the hash.
        creds = self.user._generate_verification_credentials()
        self.assertFalse(self.user._verify_email_otp("000001"))
        self.assertFalse(self.user._verify_email_otp("000002"))
        self.assertFalse(self.user._verify_email_otp("000003"))
        # Now even the correct OTP must fail because the hash was wiped.
        self.assertFalse(self.user._verify_email_otp(creds["otp"]))
        self.assertFalse(self.user.email_verification_otp_hash)

    def test_expired_otp_rejected(self):
        creds = self.user._generate_verification_credentials()
        # Manually expire the credentials.
        self.user.email_verification_expiry = (
            fields.Datetime.now() - timedelta(minutes=1)
        )
        self.assertFalse(self.user._verify_email_otp(creds["otp"]))
        # User remains unverified, but hash is intact (no attempt counted).
        self.assertFalse(self.user.email_verified)

    def test_resend_cooldown_enforced(self):
        self.user._generate_verification_credentials()
        ok, _ = self.user._can_resend_verification()
        self.assertFalse(ok)

    def test_resend_after_cooldown_allowed(self):
        self.user._generate_verification_credentials()
        # Backdate the last_sent stamp past the cooldown.
        self.user.email_verification_last_sent = (
            fields.Datetime.now() - timedelta(seconds=120)
        )
        ok, _ = self.user._can_resend_verification()
        self.assertTrue(ok)
