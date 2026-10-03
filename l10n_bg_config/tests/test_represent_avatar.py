"""Иконката на представляващия."""

import base64

from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open


@tagged("post_install", "-at_install")
class TestRepresentAvatar(TransactionCase):
    def test_represent_has_own_placeholder(self):
        company = self.env["res.partner"].create({"name": "Фирма", "is_company": True})
        represent = self.env["res.partner"].create(
            {"name": "Иван ПЕТРОВ", "type": "represent", "parent_id": company.id})
        with file_open("l10n_bg_config/static/img/represent.png", "rb") as f:
            expected = base64.b64encode(f.read())
        self.assertEqual(represent.avatar_128 and represent._avatar_get_placeholder_path(),
                         "l10n_bg_config/static/img/represent.png")
        self.assertEqual(represent.avatar_1920, expected)

    def test_contact_keeps_default_placeholder(self):
        contact = self.env["res.partner"].create({"name": "Иван", "type": "contact"})
        self.assertNotEqual(contact._avatar_get_placeholder_path(), "l10n_bg_config/static/img/represent.png")
