"""Улицата, съставена от под-полетата."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStreet(TransactionCase):
    def _partner(self, vals):
        partner = self.env["res.partner"].create({"name": "Test"})
        partner.with_context(lang="bg_BG").write(vals)
        return partner

    def test_floor_without_apartment(self):
        # етаж без апартамент вдигаше TypeError (str + False)
        partner = self._partner({"street_name": "ул. Тест", "street_number": "1", "street_floor_number": "2"})
        self.assertIn("2", partner.street)

    def test_empty_parts_with_country_keep_every_language(self):
        # празен етаж/блок, записан заедно с държавата, оставяше en_US празно
        # видимо с partner_multilang (преводима улица) и включена транслитерация
        if "bg_BG" not in dict(self.env["res.lang"].get_installed()):
            self.env["res.lang"]._activate_lang("bg_BG")
        if "transliterate_names" in self.env.company._fields:
            self.env.company.write({"country_id": self.env.ref("base.bg").id, "transliterate_names": True})
        self.env = self.env(context=dict(self.env.context, lang="bg_BG"))
        partner = self._partner({
            "street_name": "бул. Тест",
            "street_number": "105",
            "street_building_number": False,
            "street_floor_number": False,
            "country_id": self.env.ref("base.bg").id,
        })
        for lang in ("bg_BG", "en_US"):
            self.assertEqual(partner.with_context(lang=lang).street, "бул. Тест 105", lang)

    def test_apartment_without_floor(self):
        partner = self._partner({"street_name": "ул. Тест", "street_number": "1", "street_number2": "5"})
        self.assertEqual(partner.street, "ул. Тест 1 - 5")
