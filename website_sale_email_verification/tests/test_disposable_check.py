# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestDisposableCheck(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Domain = cls.env["disposable.email.domain"]

    def test_seed_domain_blocked(self):
        # mailinator.com ships in the seed list — should be blocked.
        self.assertTrue(self.Domain._is_disposable("foo@mailinator.com"))

    def test_legitimate_domain_allowed(self):
        self.assertFalse(self.Domain._is_disposable("foo@gmail.com"))

    def test_subdomain_attack_blocked(self):
        # Even though `bar.mailinator.com` isn't seeded explicitly, the
        # suffix check matches `mailinator.com`.
        self.assertTrue(self.Domain._is_disposable("foo@bar.mailinator.com"))

    def test_plus_addressing_irrelevant(self):
        # The `+` part is on the local side; the domain is gmail.com → allowed.
        self.assertFalse(self.Domain._is_disposable("foo+spam@gmail.com"))
        # Same for a blocked domain — should still be blocked.
        self.assertTrue(self.Domain._is_disposable("foo+spam@mailinator.com"))

    def test_punycode_idn(self):
        # IDN with cyrillic: this domain isn't in the blocklist; should be
        # allowed without raising even though we try to encode to punycode.
        self.assertFalse(
            self.Domain._is_disposable("foo@българия.bg"),
        )

    def test_cache_invalidation_on_create(self):
        before = self.Domain._is_disposable("foo@brand-new-throwaway.test")
        self.assertFalse(before)
        self.Domain.create({"name": "brand-new-throwaway.test", "source": "manual"})
        # After create, ormcache should have been invalidated.
        self.assertTrue(self.Domain._is_disposable("foo@brand-new-throwaway.test"))

    def test_cache_invalidation_on_unlink(self):
        rec = self.Domain.create({"name": "remove-me.test", "source": "manual"})
        self.assertTrue(self.Domain._is_disposable("foo@remove-me.test"))
        rec.unlink()
        self.assertFalse(self.Domain._is_disposable("foo@remove-me.test"))

    def test_lowercase_normalization(self):
        rec = self.Domain.create(
            {"name": "MIXED-Case-Domain.test", "source": "manual"},
        )
        self.assertEqual(rec.name, "mixed-case-domain.test")
        self.assertTrue(self.Domain._is_disposable("foo@MIXED-CASE-DOMAIN.TEST"))

    def test_empty_email(self):
        self.assertFalse(self.Domain._is_disposable(""))
        self.assertFalse(self.Domain._is_disposable("not-an-email"))
