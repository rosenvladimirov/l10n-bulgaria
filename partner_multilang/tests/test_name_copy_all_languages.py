# -*- coding: utf-8 -*-
"""Фирма в BG без транслитерация: ръчната редакция на името на един език.

Името се копира в другите езици само там, където е било същото като на
редактирания език; език със собствено име (напр. латиницата от Търговския
регистър) остава.
"""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNameCopyAllLanguages(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("bg_BG")
        cls.env.company.country_id = cls.env.ref("base.bg")
        cls.env.company.transliterate_names = False
        cls.Partner = cls.env["res.partner"]

    def _names(self, partner):
        return (partner.with_context(lang="bg_BG").name,
                partner.with_context(lang="en_US").name)

    def test_synced_languages_follow_the_edit(self):
        # и двата езика са с едно име → редакцията на български ги сменя заедно
        partner = self.Partner.with_context(lang="bg_BG").create({"name": "Стара Фирма ООД", "is_company": True})
        partner.with_context(lang="bg_BG").write({"name": "Нова Фирма ООД"})
        self.assertEqual(self._names(partner), ("Нова Фирма ООД", "Нова Фирма ООД"))

    def test_own_english_name_is_kept(self):
        # английското е собствено (от регистъра) → редакцията на български не го пипа
        partner = self.Partner.with_context(lang="bg_BG").create({"name": "Солид-55 ООД", "is_company": True})
        partner.with_context(update_lang=True).update_field_translations(
            "name", {"bg_BG": "Солид-55 ООД", "en_US": "Solid-55 Ltd."})
        partner.with_context(lang="bg_BG").write({"name": "Солид 55 ООД"})
        self.assertEqual(self._names(partner), ("Солид 55 ООД", "Solid-55 Ltd."))

    def test_own_bulgarian_name_is_kept_on_english_edit(self):
        partner = self.Partner.with_context(lang="bg_BG").create({"name": "Солид-55 ООД", "is_company": True})
        partner.with_context(update_lang=True).update_field_translations(
            "name", {"bg_BG": "Солид-55 ООД", "en_US": "Solid-55 Ltd."})
        partner.with_context(lang="en_US").write({"name": "Solid 55 Ltd."})
        self.assertEqual(self._names(partner), ("Солид-55 ООД", "Solid 55 Ltd."))
