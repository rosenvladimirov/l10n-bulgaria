# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestLinkFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({
            "email_verification_method": "link",
            "email_verification_expiry_minutes": 30,
        })
        cls.user = cls.env["res.users"].create({
            "name": "Link Test",
            "login": "link.test@example.com",
            "email_verified": False,
        })

    def test_correct_token_marks_verified(self):
        creds = self.user._generate_verification_credentials()
        self.assertTrue(self.user._verify_email_token(creds["token"]))
        self.assertTrue(self.user.email_verified)
        self.assertFalse(self.user.email_verification_token)

    def test_wrong_token_rejected(self):
        self.user._generate_verification_credentials()
        self.assertFalse(self.user._verify_email_token("not-the-real-token"))
        self.assertFalse(self.user.email_verified)
        self.assertTrue(self.user.email_verification_token)

    def test_used_token_no_longer_valid(self):
        creds = self.user._generate_verification_credentials()
        self.assertTrue(self.user._verify_email_token(creds["token"]))
        # Re-use must fail — the token field was cleared on success.
        self.assertFalse(self.user._verify_email_token(creds["token"]))

    def test_expired_token_rejected(self):
        creds = self.user._generate_verification_credentials()
        self.user.email_verification_expiry = (
            fields.Datetime.now() - timedelta(minutes=1)
        )
        self.assertFalse(self.user._verify_email_token(creds["token"]))
        self.assertFalse(self.user.email_verified)

    def test_empty_token_rejected(self):
        self.user._generate_verification_credentials()
        self.assertFalse(self.user._verify_email_token(""))
        self.assertFalse(self.user._verify_email_token(None))
