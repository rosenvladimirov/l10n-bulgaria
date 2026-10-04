# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Ключът, върнат от лицензния сървър — ADR l10n-bg-license-key-registration/0001."""
from odoo.tests import TransactionCase, tagged

from odoo.addons.l10n_bg_config.models.l10n_bg_config_mixin import is_valid_api_key


@tagged("post_install", "-at_install")
class TestRegistrationReturnedKey(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Тест Фирма ЕООД"})
        cls.partner = cls.company.partner_id

    def test_01_key_and_empty_uic_are_written_and_validate(self):
        self.partner.write({"l10n_bg_uic": False, "l10n_bg_key": False})
        self.company._l10n_bg_apply_returned_key({"l10n_bg_key": "Abc123Def", "uic": "203854036"})
        self.assertEqual(self.partner.l10n_bg_uic, "203854036")
        self.assertEqual(self.partner.l10n_bg_key, "Abc123Def")
        self.assertTrue(is_valid_api_key("203854036", "Abc123Def", self.partner.l10n_bg_crypt_key),
                        "write-ът трябва сам да изчисли crypt-а")

    def test_02_different_uic_is_not_touched(self):
        self.partner.write({"l10n_bg_uic": "BG203854036"})
        self.company._l10n_bg_apply_returned_key({"l10n_bg_key": "Abc123Def", "uic": "203854036"})
        self.assertEqual(self.partner.l10n_bg_uic, "BG203854036", "различен ЕИК не се пипа тихо")
        self.assertEqual(self.partner.l10n_bg_key, "Abc123Def")

    def test_03_no_key_in_result_changes_nothing(self):
        self.partner.write({"l10n_bg_key": "Keep12345"})
        self.assertFalse(self.company._l10n_bg_apply_returned_key({"token": "x"}))
        self.assertEqual(self.partner.l10n_bg_key, "Keep12345")

    def test_04_config_version_is_reported(self):
        self.assertTrue(self.env["res.company"]._l10n_bg_config_version().startswith("19.0."))
