# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Съветникът за превод на продуктовата страница.

Проверяваме три неща: кои елементи събира (по раздели, включително COW
изгледа на сайта), че записът минава през update_field_translations за цели
полета и за отделни термини, и че непроменените редове не се пишат.
"""

from odoo import Command
from odoo.tests import TransactionCase, tagged

ZONE_KEY = "website_sale.product_oe_structure_website_sale_product_1"
ZONE_ARCH = """
<data>
    <xpath
        expr="//*[hasclass('oe_structure')][@id='oe_structure_website_sale_product_1']"
        position="replace">
        <div class="oe_structure" id="oe_structure_website_sale_product_1">
            <p>%s</p>
        </div>
    </xpath>
</data>
"""


@tagged("post_install", "-at_install")
class TestProductPageTranslate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Lang = cls.env["res.lang"]
        Lang._activate_lang("bg_BG")
        cls.lang_en = Lang._lang_get("en_US")
        cls.lang_bg = Lang._lang_get("bg_BG")
        cls.website = cls.env["website"].create(
            {
                "name": "Translation Test Shop",
                "default_lang_id": cls.lang_en.id,
                "language_ids": [Command.set([cls.lang_en.id, cls.lang_bg.id])],
            }
        )
        cls.other_website = cls.env["website"].create({"name": "Other Shop"})
        cls.attribute = cls.env["product.attribute"].create(
            {
                "name": "Colour",
                "value_ids": [
                    Command.create({"name": "Red"}),
                    Command.create({"name": "Blue"}),
                ],
            }
        )
        cls.parent_category = cls.env["product.public.category"].create(
            {"name": "Furniture"}
        )
        cls.category = cls.env["product.public.category"].create(
            {"name": "Chairs", "parent_id": cls.parent_category.id}
        )
        cls.tag = cls.env["product.tag"].create({"name": "New Arrival"})
        cls.product = cls.env["product.template"].create(
            {
                "name": "Oak Chair",
                "sale_ok": True,
                "website_id": cls.website.id,
                "description_ecommerce": "<p>Solid oak.</p><p>Made by hand.</p>",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": cls.attribute.id,
                            "value_ids": [Command.set(cls.attribute.value_ids.ids)],
                        }
                    )
                ],
                "public_categ_ids": [Command.set(cls.category.ids)],
                "product_tag_ids": [Command.set(cls.tag.ids)],
            }
        )
        cls.main_view = cls.env.ref("website_sale.product")

    def _open(self, **vals):
        action = self.product.action_open_page_translation()
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        if vals:
            wizard.write(vals)
            wizard._load_lines()
        return wizard

    def _line(self, wizard, record, fname, source, lang="bg_BG"):
        lines = wizard.line_ids.filtered(
            lambda line: (
                line.res_model == record._name
                and line.res_id == record.id
                and line.field_name == fname
                and line.source == source
                and line.lang_id.code == lang
            )
        )
        self.assertEqual(
            len(lines), 1, f"Expected one line for {record}.{fname} {source!r}"
        )
        return lines

    def _zone_view(self, text, website):
        return self.env["ir.ui.view"].create(
            {
                "name": "Product page zone",
                "type": "qweb",
                "mode": "extension",
                "inherit_id": self.main_view.id,
                "key": ZONE_KEY,
                "website_id": website.id if website else False,
                "arch": ZONE_ARCH % text,
            }
        )

    def test_01_defaults(self):
        wizard = self._open()
        self.assertEqual(wizard.website_id, self.website)
        # en_US е основният език на сайта ⇒ остава само българският.
        self.assertEqual(wizard.lang_ids, self.lang_bg)

    def test_02_collects_every_section(self):
        wizard = self._open()
        name = self._line(wizard, self.product, "name", "Oak Chair")
        self.assertEqual(name.section, "product")
        self.assertFalse(name.value, "An untranslated plain field shows empty.")
        self.assertFalse(name.is_term)
        for term in ("Solid oak.", "Made by hand."):
            line = self._line(wizard, self.product, "description_ecommerce", term)
            self.assertTrue(line.is_term)
        self.assertEqual(
            self._line(wizard, self.attribute, "name", "Colour").section, "attribute"
        )
        for value in self.attribute.value_ids:
            self._line(wizard, value, "name", value.name)
        # Родителят влиза, защото е в трохите на страницата.
        for category in (self.category, self.parent_category):
            line = self._line(wizard, category, "name", category.name)
            self.assertEqual(line.section, "category")
        self._line(wizard, self.tag, "name", "New Arrival")
        page = wizard.line_ids.filtered(lambda line: line.section == "page")
        self.assertTrue(page)
        self.assertEqual(set(page.mapped("res_model")), {"ir.ui.view"})

    def test_03_sections_can_be_switched_off(self):
        wizard = self._open(with_page=False, with_attributes=False)
        sections = set(wizard.line_ids.mapped("section"))
        self.assertEqual(sections, {"product", "category"})

    def test_04_save_plain_field(self):
        wizard = self._open()
        self._line(wizard, self.product, "name", "Oak Chair").value = "Дъбов стол"
        wizard.action_save()
        self.assertEqual(self.product.with_context(lang="bg_BG").name, "Дъбов стол")
        self.assertEqual(self.product.with_context(lang="en_US").name, "Oak Chair")
        # Редовете се презареждат с новото състояние.
        line = self._line(wizard, self.product, "name", "Oak Chair")
        self.assertEqual(line.value, "Дъбов стол")
        self.assertEqual(line.original_value, "Дъбов стол")

    def test_05_save_single_html_term(self):
        wizard = self._open()
        line = self._line(wizard, self.product, "description_ecommerce", "Solid oak.")
        line.value = "Масивен дъб."
        wizard.action_save()
        html_bg = self.product.with_context(lang="bg_BG").description_ecommerce
        self.assertIn("Масивен дъб.", html_bg)
        self.assertIn("Made by hand.", html_bg, "Other terms keep the source.")
        html_en = self.product.with_context(lang="en_US").description_ecommerce
        self.assertIn("Solid oak.", html_en)

    def test_06_only_missing(self):
        self.product.update_field_translations("name", {"bg_BG": "Дъбов стол"})
        wizard = self._open(only_missing=True)
        self.assertFalse(
            wizard.line_ids.filtered(
                lambda line: (
                    line.res_model == "product.template" and line.field_name == "name"
                )
            )
        )
        self._line(wizard, self.product, "description_ecommerce", "Made by hand.")

    def test_07_clearing_removes_translation(self):
        self.product.update_field_translations("name", {"bg_BG": "Дъбов стол"})
        wizard = self._open()
        self._line(wizard, self.product, "name", "Oak Chair").value = ""
        wizard.action_save()
        self.assertEqual(self.product.with_context(lang="bg_BG").name, "Oak Chair")

    def test_08_unchanged_lines_are_not_written(self):
        wizard = self._open()
        self.assertEqual(dict(wizard._collect_changes()), {})
        self._line(wizard, self.tag, "name", "New Arrival").value = "Ново"
        changes = wizard._collect_changes()
        self.assertEqual(
            dict(changes),
            {("product.tag", self.tag.id, "name"): {"bg_BG": "Ново"}},
        )

    def test_09_website_specific_zone_wins(self):
        self._zone_view("Shipping for all websites", website=False)
        specific = self._zone_view("Free shipping over 50 EUR", website=self.website)
        self._zone_view("Other shop banner", website=self.other_website)
        wizard = self._open()
        page_sources = wizard.line_ids.filtered(
            lambda line: line.section == "page"
        ).mapped("source")
        self.assertIn("Free shipping over 50 EUR", page_sources)
        self.assertNotIn("Shipping for all websites", page_sources)
        self.assertNotIn("Other shop banner", page_sources)

        line = self._line(wizard, specific, "arch_db", "Free shipping over 50 EUR")
        self.assertEqual(line.field_label, "Template")
        line.value = "Безплатна доставка над 50 EUR"
        wizard.action_save()
        self.assertIn(
            "Безплатна доставка над 50 EUR",
            specific.with_context(lang="bg_BG").arch_db,
        )

    def test_10_follows_t_call_and_skips_site_layout(self):
        View = self.env["ir.ui.view"]
        View.create(
            {
                "name": "Called from the product page",
                "type": "qweb",
                "key": "website_sale_product_page_translate.test_called",
                "arch": "<t><p>Delivery in two days</p></t>",
            }
        )
        View.create(
            {
                "name": "Product page calls a sub-template",
                "type": "qweb",
                "mode": "extension",
                "inherit_id": self.main_view.id,
                "key": "website_sale_product_page_translate.test_caller",
                "arch": """
<data>
    <xpath expr="//div[@id='product_full_description']" position="after">
        <t t-call="website_sale_product_page_translate.test_called"/>
    </xpath>
</data>
""",
            }
        )
        wizard = self._open()
        page = wizard.line_ids.filtered(lambda line: line.section == "page")
        self.assertIn("Delivery in two days", page.mapped("source"))
        page_views = View.browse(set(page.mapped("res_id")))
        # Подшаблон на ядрото, извикан от самата страница.
        self.assertIn("website_sale.cta_wrapper", page_views.mapped("key"))
        # Обвивката на сайта не е част от страницата.
        self.assertNotIn("website.layout", page_views.mapped("key"))
        # Термините само от пунктуация („:“ в шаблоните на ядрото) отпадат.
        self.assertFalse(
            [s for s in page.mapped("source") if not any(c.isalpha() for c in s)]
        )

    def test_11_bulgarian_website_edits_the_english_source(self):
        """Сайт с основен език български (като в Пакит): преводът е към en_US.

        Продуктът е въведен на български ⇒ en_US държи същия текст. Редът en_US
        поправя изхода, а българският текст трябва да остане непокътнат.
        """
        website = self.env["website"].create(
            {
                "name": "Bulgarian Shop",
                "default_lang_id": self.lang_bg.id,
                "language_ids": [Command.set([self.lang_en.id, self.lang_bg.id])],
            }
        )
        product = (
            self.env["product.template"]
            .with_context(lang="bg_BG")
            .create(
                {
                    "name": "Кашон",
                    "sale_ok": True,
                    "website_id": website.id,
                    "description_ecommerce": "<p>Петслоен.</p><p>За износ.</p>",
                }
            )
        )
        action = product.action_open_page_translation()
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(wizard.lang_ids, self.lang_en)
        self._line(wizard, product, "name", "Кашон", lang="en_US").value = "Box"
        line = self._line(
            wizard, product, "description_ecommerce", "Петслоен.", lang="en_US"
        )
        line.value = "Five-ply."
        wizard.action_save()
        en = product.with_context(lang="en_US")
        bg = product.with_context(lang="bg_BG")
        self.assertEqual(en.name, "Box")
        self.assertEqual(bg.name, "Кашон")
        self.assertIn("Five-ply.", en.description_ecommerce)
        self.assertIn("За износ.", en.description_ecommerce)
        self.assertIn("Петслоен.", bg.description_ecommerce)
        self.assertNotIn("Five-ply.", bg.description_ecommerce)

    def test_12_values_without_letters_are_skipped(self):
        size = self.env["product.attribute.value"].create(
            {"name": "180×100×50", "attribute_id": self.attribute.id}
        )
        self.product.attribute_line_ids.value_ids = [Command.link(size.id)]
        wizard = self._open()
        self.assertFalse(
            wizard.line_ids.filtered(
                lambda line: line.res_model == size._name and line.res_id == size.id
            )
        )
        self._line(wizard, self.attribute.value_ids[0], "name", "Red")
