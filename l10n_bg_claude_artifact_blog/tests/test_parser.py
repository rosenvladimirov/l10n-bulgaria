# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Парсерът се мери по НОСЕНОТО съдържание, не по броя блокове.

Всяко от тези твърдения идва от реален дефект, намерен срещу истински
артефакти: изядена таблица в <details>, изгубен трети <span> в показател,
разтворен <dl class="stat">, подпис на фигура в нищото.
"""

import re

from lxml import html as lxml_html

from odoo.tests.common import TransactionCase

from .fixtures.sample_artifact import ARTIFACT_HTML, ARTIFACT_MARKDOWN

WORD_RE = re.compile(r"[\wЀ-ӿ%]+", re.UNICODE)


class TestArtifactParser(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parser = cls.env["claude.artifact.parser"]
        cls.title, cls.blocks = cls.parser.parse(ARTIFACT_HTML)

    # ------------------------------------------------------------------
    def _kinds(self):
        kinds = {}
        for block in self.blocks:
            kinds[block["kind"]] = kinds.get(block["kind"], 0) + 1
        return kinds

    def _carried_words(self):
        carried = [self.title]
        for block in self.blocks:
            carried.append(block["text"])
            if block["html"]:
                try:
                    fragment = lxml_html.fragment_fromstring(
                        block["html"], create_parent="div")
                    carried.append(" ".join(fragment.itertext()))
                except Exception:  # pragma: no cover - повреден фрагмент
                    carried.append(block["html"])
            carried.extend(str(value) for value in block["meta"].values())
        return set(WORD_RE.findall(" ".join(carried).lower()))

    # ------------------------------------------------------------------
    def test_title_comes_from_the_head(self):
        self.assertEqual(self.title, "Разчетът на склада")

    def test_h1_that_repeats_the_title_is_dropped(self):
        headings = [block for block in self.blocks
                    if block["kind"] == "heading" and block["level"] == 1]
        self.assertFalse(
            headings,
            "Заглавието се рендира от блога; повторен h1 прави две заглавия.")

    def test_eyebrow_and_standfirst_are_recognised(self):
        kinds = self._kinds()
        self.assertEqual(kinds.get("kicker"), 1)
        self.assertEqual(kinds.get("standfirst"), 1)

    def test_stat_list_becomes_a_figures_board(self):
        boards = [block for block in self.blocks if block["kind"] == "kpi_group"]
        self.assertEqual(len(boards), 1, "<dl class='stat'> е табло, не списък")
        pairs = boards[0]["meta"]["pairs"]
        self.assertEqual(len(pairs), 3)
        self.assertEqual(pairs[0]["label"], "партиди")
        self.assertEqual(pairs[0]["value"], "18")
        self.assertEqual(pairs[0]["note"], "от 4 200 общо")

    def test_kpi_keeps_every_span(self):
        """Третият <span> в показател си отиваше тихо — 145 думи на артефакт."""
        kpis = [block for block in self.blocks if block["kind"] == "kpi"]
        self.assertEqual(len(kpis), 1)
        self.assertEqual(kpis[0]["meta"]["number"], "49")
        self.assertIn("от които 7 с изтекъл срок", kpis[0]["meta"]["label"])

    def test_table_inside_details_inside_figure_survives(self):
        """Фигурата носи и диаграма, и таблица — вземахме само първото."""
        accordions = [block for block in self.blocks if block["kind"] == "accordion"]
        self.assertEqual(len(accordions), 1)
        self.assertIn("<table>", accordions[0]["html"])
        self.assertIn("август", accordions[0]["html"])

    def test_figure_caption_is_carried(self):
        svgs = [block for block in self.blocks if block["kind"] == "svg"]
        self.assertEqual(len(svgs), 1)
        self.assertIn("Партиди без движение по месеци",
                      svgs[0]["meta"].get("caption", ""))

    def test_diagram_keeps_its_colours(self):
        """Правилата стоят на `.chart .bar`, а обвивката .chart не пътува към
        статията: без пренасяне всяка диаграма излиза черна."""
        svg = [block for block in self.blocks if block["kind"] == "svg"][0]
        self.assertTrue(svg["meta"]["styled"])
        self.assertIn("#0E6B5E", svg["html"], "цветът на артефакта трябва да е инлайнван")
        self.assertNotIn("var(--", svg["html"], "променливите трябва да са разрешени")

    def test_artifact_css_never_leaks_into_the_page(self):
        """Вграден <style> в inline SVG важи за ЦЯЛАТА страница, не за SVG-то."""
        svg = [block for block in self.blocks if block["kind"] == "svg"][0]
        self.assertNotIn("<style", svg["html"])

    def test_code_keeps_language_and_body(self):
        codes = [block for block in self.blocks if block["kind"] == "code"]
        self.assertEqual(len(codes), 1)
        self.assertEqual(codes[0]["lang"], "python")
        self.assertIn("def total(lines):", codes[0]["text"])
        self.assertIn("return sum(line.qty for line in lines)", codes[0]["text"])

    def test_emoji_marker_makes_a_callout(self):
        callouts = [block for block in self.blocks if block["kind"] == "callout"]
        self.assertEqual(len(callouts), 1)
        self.assertEqual(callouts[0]["meta"]["level"], "warning")

    def test_quote_keeps_its_cite(self):
        quotes = [block for block in self.blocks if block["kind"] == "quote"]
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0]["meta"]["cite"], "работна бележка")

    def test_script_and_style_never_reach_the_blocks(self):
        blob = " ".join(block["html"] + block["text"] for block in self.blocks)
        self.assertNotIn("console.log", blob)
        self.assertNotIn("font-family", blob)

    def test_inline_attributes_are_stripped_but_links_survive(self):
        paragraphs = [block for block in self.blocks
                      if block["kind"] == "paragraph" and "препратка" in block["text"]]
        self.assertTrue(paragraphs)
        self.assertIn('href="https://example.org/doc"', paragraphs[0]["html"])
        self.assertIn("<b>", paragraphs[0]["html"])

    def test_no_content_is_lost(self):
        """Контролното число: всеки листен елемент на източника е пренесен."""
        carried = self._carried_words()
        tree = lxml_html.fromstring(ARTIFACT_HTML)
        for tag in ("script", "style", "head", "noscript"):
            for node in tree.xpath("//%s" % tag):
                node.getparent().remove(node)
        missing = []
        for element in tree.iter():
            if not isinstance(element.tag, str):
                continue
            if [child for child in element if isinstance(child.tag, str)]:
                continue
            words = set(WORD_RE.findall(element.text_content().lower()))
            if words and not words.issubset(carried):
                missing.append((element.tag, element.text_content().strip()[:60]))
        self.assertFalse(missing, "непренесени елементи: %s" % missing)

    def test_text_after_an_inline_tag_is_not_emitted_twice(self):
        """lxml слага tail-а на елемента в tostring(); текстът след <code>
        влизаше веднъж в блока и втори път като отделен параграф — цял
        артефакт излизаше с 15% повече думи, отколкото има."""
        source = ("<html><body><div class='sources'>Източници: "
                  "<code>alpha.md</code> (първи) · <code>beta.md</code> (втори)"
                  "</div></body></html>")
        _title, blocks = self.parser.parse(source)
        carried = " ".join(block["html"] for block in blocks)
        self.assertEqual(carried.count("(първи)"), 1, carried)
        self.assertEqual(carried.count("(втори)"), 1, carried)
        self.assertEqual(carried.count("alpha.md"), 1, carried)

    def test_text_between_inline_tags_survives(self):
        """Обратната грешка: с with_tail=False изчезва текстът МЕЖДУ таговете."""
        source = "<html><body><p>ляво <b>смело</b> средно <i>косо</i> дясно</p></body></html>"
        _title, blocks = self.parser.parse(source)
        self.assertEqual(len(blocks), 1)
        for word in ("ляво", "смело", "средно", "косо", "дясно"):
            self.assertIn(word, blocks[0]["html"])

    # ------------------------------------------------------------------
    def test_markdown_source_is_parsed_too(self):
        title, blocks = self.parser.parse(ARTIFACT_MARKDOWN, "markdown")
        kinds = {}
        for block in blocks:
            kinds[block["kind"]] = kinds.get(block["kind"], 0) + 1
        self.assertEqual(title, "Разчетът на склада")
        self.assertEqual(kinds.get("heading"), 2, "двете h2 заглавия")
        self.assertEqual(kinds.get("code"), 1)
        self.assertEqual(kinds.get("table"), 1)
        self.assertEqual(kinds.get("list"), 1)
        self.assertEqual(kinds.get("quote"), 1)
        self.assertEqual(kinds.get("separator", 0), 1)
        code = [block for block in blocks if block["kind"] == "code"][0]
        self.assertEqual(code["lang"], "python")
        self.assertIn("def total(lines):", code["text"])
