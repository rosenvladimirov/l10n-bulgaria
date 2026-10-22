# -*- coding: utf-8 -*-
"""Транслитерацията по Закона за транслитерацията и езикът на записа.

1. ``transliterate_bg`` — таблицата на чл. 4, „ия“ в края на думата, „България“.
2. Езикът се взема от контекста на записа, не от потребителя: потребител с
   български интерфейс, който пише с lang=en_US (импорт, RPC, съветник), иначе
   оставя bg_BG празен и българският превод показва латиницата.
3. Длъжността не се транслитерира; адресът — само с настройката на фирмата.
"""

from odoo.tests import TransactionCase, tagged

from odoo.addons.partner_multilang.models.res_transliterate import (
    partner_name_translate,
    transliterate_bg,
)


@tagged("post_install", "-at_install")
class TestTransliterateBg(TransactionCase):

    def test_law_table(self):
        cases = {
            "Хаджи Димитър": "Hadzhi Dimitar",
            "Щастливец ЕООД": "Shtastlivets EOOD",
            "Ъгъл Юг Яворов": "Agal Yug Yavorov",
            "Жълти цветя": "Zhalti tsvetya",
            "ул. Цар Освободител": "ul. Tsar Osvoboditel",
            "Йорданка Георгиева": "Yordanka Georgieva",
        }
        for cyr, latin in cases.items():
            self.assertEqual(transliterate_bg(cyr), latin, cyr)

    def test_ia_at_word_end(self):
        # чл. 4, ал. 2 — само в края на думата
        self.assertEqual(transliterate_bg("гр. София"), "gr. Sofia")
        self.assertEqual(transliterate_bg("Мария Илиева"), "Maria Ilieva")
        self.assertEqual(transliterate_bg("Юлиян"), "Yuliyan")

    def test_bulgaria(self):
        # чл. 4, ал. 3
        self.assertEqual(transliterate_bg("бул. България 1"), "bul. Bulgaria 1")
        self.assertEqual(transliterate_bg("БЪЛГАРИЯ"), "BULGARIA")

    def test_upper_case_words(self):
        self.assertEqual(transliterate_bg("Иван ЖЕЛЕВ"), "Ivan ZHELEV")
        self.assertEqual(transliterate_bg("ТЕХНО-ЛОГИСТИК ЕООД"), "TEHNO-LOGISTIK EOOD")
        self.assertEqual(transliterate_bg("Ж"), "Zh")

    def test_latin_and_digits_unchanged(self):
        self.assertEqual(transliterate_bg('"Пакит.БГ" ЕООД, PACKIT 2'), '"Pakit.BG" EOOD, PACKIT 2')

    def test_partner_name_translate_uses_law_for_bg(self):
        self.assertEqual(partner_name_translate("София", "bg_BG", True), "Sofia")


@tagged("post_install", "-at_install")
class TestTransliterationLanguage(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        bg = cls.env["res.lang"]._activate_lang("bg_BG")
        bg.transliterate = True
        cls.env.company.country_id = cls.env.ref("base.bg")
        cls.env.company.transliterate_names = True
        cls.env.company.transliterate_addresses = False
        cls.env.user.lang = "bg_BG"
        cls.germany = cls.env.ref("base.de")
        cls.Partner = cls.env["res.partner"]

    def _value(self, partner, fname, lang):
        return partner.with_context(lang=lang)[fname]

    def test_cyrillic_written_in_english_context_keeps_bulgarian(self):
        # български потребител, запис с lang=en_US (импорт/RPC): кирилицата е
        # българското име, а не английското
        partner = self.Partner.with_context(lang="en_US").create(
            {"name": "Мария Иванова", "country_id": self.germany.id})
        self.assertEqual(self._value(partner, "name", "bg_BG"), "Мария Иванова")
        self.assertEqual(self._value(partner, "name", "en_US"), "Maria Ivanova")

    def test_function_is_not_transliterated(self):
        partner = self.Partner.with_context(lang="bg_BG").create(
            {"name": "Иван Петров", "function": "Управител", "country_id": self.germany.id})
        self.assertNotEqual(self._value(partner, "function", "en_US"), "Upravitel")

    def test_address_only_with_setting(self):
        vals = {"name": "Иван Петров", "street": "ул. Цар Освободител 1", "country_id": self.germany.id}
        if not self.Partner._fields["street"].translate:
            self.skipTest("адресът не е преводим без l10n_bg_multilang")
        partner = self.Partner.with_context(lang="bg_BG").create(dict(vals))
        self.assertNotEqual(self._value(partner, "street", "en_US"), "ul. Tsar Osvoboditel 1")
        self.env.company.transliterate_addresses = True
        partner = self.Partner.with_context(lang="bg_BG").create(dict(vals))
        self.assertEqual(self._value(partner, "street", "en_US"), "ul. Tsar Osvoboditel 1")
