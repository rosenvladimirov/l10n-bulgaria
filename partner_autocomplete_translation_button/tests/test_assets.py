# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Проверки на сървърната страна на ресурсите на модула.

Самото рендиране в браузъра се проверява от hoot теста в static/tests. Тук
проверяваме това, което сървърът решава: дали шаблонът и стилът влизат в
web.assets_backend след partner_autocomplete, дали разширението се парсва
като разширение на правилния шаблон, дали след прилагане на наследяванията
бутонът за превод попада в клона с автодовършване и дали SCSS-ът се
компилира без грешка.
"""

from lxml import etree

from odoo.tests import TransactionCase, tagged
from odoo.tools.template_inheritance import apply_inheritance_specs

MODULE = "partner_autocomplete_translation_button"
PARENT = "partner_autocomplete.PartnerAutoCompleteCharField"
XML_PATH = f"/{MODULE}/static/src/xml/{MODULE}.xml"
SCSS_PATH = f"/{MODULE}/static/src/scss/{MODULE}.scss"


@tagged("post_install", "-at_install")
class TestAssets(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Същите параметри, с които ir.qweb строи пакета (website добавя
        # website_id), за да гледаме реалния списък, а не вариант без тях.
        asset = cls.env["ir.asset"]
        cls.backend_paths = [
            path
            for path, *_rest in asset._get_asset_paths(
                "web.assets_backend", asset._get_asset_params()
            )
        ]

    def _templates(self, bundle):
        """Връща (шаблони по име, разширения по родител) от XML блоковете."""
        templates, extensions = {}, {}
        for block in bundle.xml():
            if block["type"] == "templates":
                for element, _url, _inherit_from in block["templates"]:
                    templates[element.get("t-name")] = element
            else:
                for inherit_from, elements in block["extensions"].items():
                    extensions.setdefault(inherit_from, []).extend(elements)
        return templates, extensions

    def test_01_assets_in_backend_bundle_after_parent(self):
        self.assertIn(XML_PATH, self.backend_paths)
        self.assertIn(SCSS_PATH, self.backend_paths)
        parent_xml = "/partner_autocomplete/static/src/xml/partner_autocomplete.xml"
        self.assertIn(parent_xml, self.backend_paths)
        self.assertGreater(
            self.backend_paths.index(XML_PATH),
            self.backend_paths.index(parent_xml),
            "The extension must be loaded after the template it extends.",
        )

    def test_02_extension_puts_button_in_autocomplete_branch(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle(
            "web.assets_backend", css=False, js=True
        )
        templates, extensions = self._templates(bundle)
        ours = [el for el, url in extensions.get(PARENT, []) if url == XML_PATH]
        self.assertEqual(len(ours), 1, "Exactly one extension of the parent.")

        # Сглобяваме шаблона, както го прави клиентът: web.CharField →
        # първичното наследяване на partner_autocomplete → нашето разширение.
        arch = etree.fromstring(etree.tostring(templates["web.CharField"]))
        for spec_owner in (templates[PARENT], ours[0]):
            specs = [etree.fromstring(etree.tostring(s)) for s in spec_owner]
            arch = apply_inheritance_specs(arch, specs)

        autocomplete = arch.xpath("//PartnerAutoComplete")
        self.assertEqual(len(autocomplete), 1)
        branch = autocomplete[0].getparent()
        self.assertIsNotNone(branch.get("t-elif"))
        buttons = autocomplete[0].getnext()
        self.assertIsNotNone(buttons)
        self.assertEqual(buttons.get("class"), "o_field_input_buttons")
        self.assertEqual(buttons.get("t-if"), "isTranslatable")
        translation = buttons.xpath("./TranslationButton")
        self.assertEqual(len(translation), 1)
        self.assertEqual(translation[0].get("fieldName"), "props.name")
        self.assertEqual(translation[0].get("record"), "props.record")
        # Бутонът на ядрото в t-else остава непокътнат.
        self.assertEqual(len(arch.xpath("//t[@t-else='']//TranslationButton")), 1)

    def test_03_scss_compiles(self):
        # Отделен малък пакет: помощниците на web (дават
        # $o-field-translate-padding) + нашият файл, за да не компилираме
        # целия web.assets_backend в теста.
        bundle_name = f"{MODULE}.test_scss"
        self.env["ir.asset"].create(
            [
                {
                    "name": "web helpers",
                    "bundle": bundle_name,
                    "directive": "include",
                    "path": "web._assets_helpers",
                },
                {
                    "name": "module scss",
                    "bundle": bundle_name,
                    "path": SCSS_PATH.lstrip("/"),
                },
            ]
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle(
            bundle_name, css=True, js=False
        )
        css = bundle.preprocess_css()
        self.assertFalse(bundle.css_errors, "\n".join(bundle.css_errors))
        self.assertIn(".o_field_field_partner_autocomplete", css)
        self.assertIn("o-autocomplete--input", css)
        self.assertIn("35px", css)
