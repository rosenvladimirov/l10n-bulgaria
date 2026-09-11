# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Сглобяването се проверява срещу РЕАЛНИЯ markup на Odoo 19 снипетите.

Пълна база не значи работещ екран: ако class-ът не е този, който website
редакторът очаква, статията изглежда наред и не се редактира.
"""

import re

from lxml import html as lxml_html

from odoo.tests.common import TransactionCase

from .fixtures.sample_artifact import ARTIFACT_HTML

WORD_RE = re.compile(r"[\wЀ-ӿ%]+", re.UNICODE)


class TestArtifactBuilder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.artifact = cls.env["claude.artifact"].create({
            "name": "Разчетът на склада",
            "raw_source": ARTIFACT_HTML,
        })
        cls.artifact.action_parse()
        cls.artifact.action_build()
        cls.content = cls.artifact.built_content or ""
        cls.tree = lxml_html.fromstring("<div>%s</div>" % cls.content)

    def _classes(self):
        found = set()
        for element in self.tree.iter():
            if isinstance(element.tag, str):
                found.update((element.get("class") or "").split())
        return found

    # ------------------------------------------------------------------
    def test_content_is_built_from_real_odoo_snippets(self):
        classes = self._classes()
        for snippet in ("s_text_block", "s_title", "s_alert", "s_blockquote",
                        "s_big_number", "s_accordion", "s_hr"):
            self.assertIn(snippet, classes, "липсва снипет %s" % snippet)

    def test_every_section_declares_its_snippet_for_the_editor(self):
        """Без data-snippet редакторът не знае какво държи в ръцете си."""
        sections = self.tree.xpath("//section")
        self.assertTrue(sections)
        for section in sections:
            self.assertTrue(
                section.get("data-snippet"),
                "секция без data-snippet: %s" % (section.get("class") or ""),
            )

    def test_headings_open_sections_and_carry_anchors(self):
        titles = self.tree.xpath("//section[contains(@class, 's_title')]//h2")
        self.assertEqual(len(titles), 4, "четирите h2 на артефакта")
        for heading in titles:
            self.assertEqual(heading.get("data-anchor"), "true")
            self.assertRegex(
                heading.get("id") or "",
                r"^table_of_content_heading_\d+_\d+$",
                "редакторът разпознава само този вид котва",
            )

    def test_table_of_content_is_added_and_links_match_the_anchors(self):
        navbars = self.tree.xpath("//div[contains(@class, 's_table_of_content_navbar')]")
        self.assertTrue(navbars, "четири заглавия минават прага за оглавление")
        links = [link.get("href") for link
                 in self.tree.xpath("//a[contains(@class, 'table_of_content_link')]")]
        anchors = ["#%s" % heading.get("id")
                   for heading in self.tree.xpath("//h2[@data-anchor='true']")]
        self.assertEqual(links, anchors, "линк, който не сочи котва, е счупен скрол")

    def test_alert_level_follows_the_marker(self):
        alerts = self.tree.xpath(
            "//div[contains(concat(' ', normalize-space(@class), ' '), ' s_alert ')]")
        self.assertEqual(len(alerts), 1)
        self.assertIn("alert-warning", alerts[0].get("class"))

    def test_code_is_rendered_as_pre_code_not_as_paragraph(self):
        blocks = self.tree.xpath("//pre/code")
        self.assertEqual(len(blocks), 1)
        self.assertIn("def total(lines):", blocks[0].text_content())

    def test_table_is_wrapped_in_its_own_scroller(self):
        """Широка таблица без обвивка вади цялата страница настрани."""
        tables = self.tree.xpath("//table")
        self.assertTrue(tables)
        for table in tables:
            wrapper = table.getparent()
            self.assertIn(
                "table-responsive", (wrapper.get("class") or ""),
                "таблица без .table-responsive",
            )

    def test_figures_board_renders_every_pair(self):
        board = self.tree.xpath("//section[@data-name='Figures']")
        self.assertTrue(board)
        values = [node.text_content().strip()
                  for node in board[0].xpath(".//h3")]
        self.assertEqual(values, ["18", "935", "5"])

    def test_accordion_ids_are_unique_and_wired(self):
        button = self.tree.xpath("//button[contains(@class, 'accordion-button')]")[0]
        panel_id = button.get("data-bs-target")
        self.assertTrue(panel_id.startswith("#"))
        panels = self.tree.xpath("//div[@id='%s']" % panel_id[1:])
        self.assertEqual(len(panels), 1, "бутонът трябва да сочи точно един панел")

    def test_svg_diagram_survives_into_the_article(self):
        svgs = self.tree.xpath("//svg")
        self.assertEqual(len(svgs), 1)
        self.assertIn("18 · юни", svgs[0].text_content())

    def test_script_never_reaches_the_article(self):
        self.assertNotIn("console.log", self.content)
        self.assertFalse(self.tree.xpath("//script"))

    def test_coverage_report_counts_the_article_not_the_blocks(self):
        report = self.artifact._coverage_report()
        self.assertGreaterEqual(
            report["coverage"], 95.0,
            "сглобената статия трябва да носи текста на артефакта: %s" % report,
        )

    def test_excluded_block_is_skipped(self):
        block = self.artifact.block_ids.filtered(lambda b: b.kind == "code")
        block.excluded = True
        self.artifact.action_build()
        self.assertNotIn("def total(lines):", self.artifact.built_content)
        block.excluded = False
        self.artifact.action_build()
        self.assertIn("def total(lines):", self.artifact.built_content)

    def test_table_of_content_can_be_turned_off(self):
        self.artifact.use_table_of_content = "never"
        self.artifact.action_build()
        self.assertNotIn("s_table_of_content", self.artifact.built_content)
        self.artifact.use_table_of_content = "auto"
        self.artifact.action_build()
        self.assertIn("s_table_of_content", self.artifact.built_content)
