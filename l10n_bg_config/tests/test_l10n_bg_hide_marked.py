from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestL10nBgHideMarked(TransactionCase):
    """Скриване по име на маркираното с l10n_bg в изгледите на не-българска фирма."""

    def _hide(self, arch, view_type="form"):
        doc = etree.fromstring(arch)
        self.env["res.partner"]._l10n_bg_hide_marked(doc, view_type)
        return doc

    def test_marked_field_and_its_label_are_hidden(self):
        doc = self._hide(
            '<form><label for="l10n_bg_uic"/><field name="l10n_bg_uic"/>'
            '<field name="name"/><field name="is_l10n_bg_record"/></form>'
        )
        self.assertEqual(doc.find("field[@name='l10n_bg_uic']").get("invisible"), "True")
        self.assertEqual(doc.find("label").get("invisible"), "True")
        self.assertIsNone(doc.find("field[@name='name']").get("invisible"))
        self.assertIsNone(doc.find("field[@name='is_l10n_bg_record']").get("invisible"))

    def test_required_field_is_not_hidden(self):
        # поле с required=True в модела остава видимо — иначе записът гърми невидимо
        self.patch(self.env["res.partner"]._fields["l10n_bg_uic"], "required", True)
        doc = self._hide('<form><field name="l10n_bg_uic"/></form>')
        self.assertIsNone(doc.find("field").get("invisible"))

    def test_required_in_view_is_not_hidden(self):
        doc = self._hide('<form><field name="l10n_bg_uic" required="1"/></form>')
        self.assertIsNone(doc.find("field").get("invisible"))

    def test_marked_page_is_hidden_unless_it_holds_a_required_field(self):
        doc = self._hide(
            '<form><notebook>'
            '<page name="l10n_bg_nra" string="NRA"><field name="name"/></page>'
            '<page name="other" string="Other"><field name="l10n_bg_uic"/></page>'
            '</notebook></form>'
        )
        pages = doc.findall(".//page")
        self.assertEqual(pages[0].get("invisible"), "True")
        self.assertIsNone(pages[1].get("invisible"))
        self.patch(self.env["res.partner"]._fields["name"], "required", True)
        doc = self._hide(
            '<form><page name="l10n_bg_nra"><field name="name"/></page></form>'
        )
        self.assertIsNone(doc.find("page").get("invisible"))

    def test_required_in_nested_list_does_not_keep_the_page(self):
        # задължително поле на реда в o2m не пази таба на родителя
        self.patch(self.env["res.partner"]._fields["l10n_bg_uic"], "required", True)
        doc = self._hide(
            '<form><page name="l10n_bg_children"><field name="child_ids"><list>'
            '<field name="l10n_bg_uic"/></list></field></page></form>'
        )
        self.assertEqual(doc.find("page").get("invisible"), "True")
        self.assertIsNone(doc.find(".//list/field").get("column_invisible"))

    def test_nested_list_column_uses_column_invisible(self):
        doc = self._hide(
            '<form><field name="child_ids"><list>'
            '<field name="l10n_bg_uic"/></list></field></form>'
        )
        column = doc.find(".//list/field")
        self.assertEqual(column.get("column_invisible"), "True")
        self.assertIsNone(column.get("invisible"))

    def test_marker_must_start_the_name(self):
        # маркерът е в НАЧАЛОТО: „съдържа l10n_bg“ не стига
        doc = self._hide(
            '<form><group id="x_l10n_bg_side"><field name="name"/></group>'
            '<div name="l10n_bg_side"><field name="name"/></div></form>'
        )
        self.assertIsNone(doc.find("group").get("invisible"))
        self.assertEqual(doc.find("div").get("invisible"), "True")

    def test_any_element_by_id_or_name(self):
        doc = self._hide(
            '<form><header><button name="l10n_bg_send" string="Send" type="object"/></header>'
            '<div id="l10n_bg_box"/><setting id="l10n_bg_setting"/>'
            '<block name="l10n_bg_block"/><separator name="l10n_bg_sep"/>'
            '<div id="other_box"/></form>'
        )
        for xpath in ("//button", "//div[@id='l10n_bg_box']", "//setting", "//block", "//separator"):
            self.assertEqual(doc.xpath(xpath)[0].get("invisible"), "True", xpath)
        self.assertIsNone(doc.xpath("//div[@id='other_box']")[0].get("invisible"))

    def test_list_and_search(self):
        doc = self._hide('<list><field name="l10n_bg_uic"/></list>', "list")
        self.assertEqual(doc.find("field").get("column_invisible"), "True")
        doc = self._hide(
            "<search><filter name=\"f\" domain=\"[('l10n_bg_uic', '!=', False)]\"/></search>",
            "search",
        )
        self.assertEqual(doc.find("filter").get("invisible"), "True")
        doc = self._hide(
            '<search><field name="l10n_bg_uic"/><field name="name"/>'
            "<filter name=\"g\" context=\"{'group_by': 'x_l10n_bg'}\"/></search>",
            "search",
        )
        self.assertEqual(doc.find("field[@name='l10n_bg_uic']").get("invisible"), "True")
        self.assertIsNone(doc.find("field[@name='name']").get("invisible"))
        self.assertIsNone(doc.find("filter").get("invisible"))

    def test_get_view_only_for_non_bg_company(self):
        foreign = self.env["res.company"].create({"name": "GR test", "country_id": self.env.ref("base.gr").id})
        self.assertNotEqual(foreign.chart_template, "bg")
        partner = self.env["res.partner"].with_company(foreign).with_context(allowed_company_ids=[foreign.id])
        arch = partner.get_view(view_type="form")["arch"]
        doc = etree.fromstring(arch)
        marked = [f for f in doc.iter("field") if "l10n_bg" in (f.get("name") or "") and f.get("name") != "is_l10n_bg_record"]
        self.assertTrue(marked, "the partner form is expected to carry l10n_bg fields")
        for field in marked:
            if not partner._l10n_bg_field_required(field):
                self.assertTrue(field.get("invisible") == "True" or field.get("column_invisible") == "True", field.get("name"))
