# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Структурите на артефакта оцеляват като структури (ADR l10n-bg-claude-artifact-blog/0004).

Всяко твърдение идва от статия на живия блог, в която таблото, картите и
стъпките излизаха като редуващи се абзаци: „мащабът", „Да — и…", „6", „30",
а номерът на всяка секция висеше самотен над заглавието ѝ.
"""

from lxml import html as lxml_html

from odoo.tests.common import TransactionCase

from .fixtures.sample_artifact import RICH_ARTIFACT_HTML

SUBTITLE = "Какво се мени между двете версии и колко струва преходът."


class TestArtifactStructures(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parser = cls.env["claude.artifact.parser"]
        cls.title, cls.blocks = cls.parser.parse(RICH_ARTIFACT_HTML)
        cls.artifact = cls.env["claude.artifact"].create({
            "name": "Одитът на склада",
            "raw_source": RICH_ARTIFACT_HTML,
        })
        cls.artifact.action_parse()
        cls.artifact.action_build()
        cls.content = cls.artifact.built_content or ""
        cls.tree = lxml_html.fromstring("<div>%s</div>" % cls.content)

    def _of(self, kind):
        return [block for block in self.blocks if block["kind"] == kind]

    def _by_class(self, name, tag="*"):
        return self.tree.xpath(
            "//%s[contains(concat(' ', normalize-space(@class), ' '), ' %s ')]" % (tag, name))

    # ------------------------------------------------------------------
    # Парсерът
    # ------------------------------------------------------------------
    def test_label_value_pairs_become_a_figures_board(self):
        boards = self._of("kpi_group")
        self.assertEqual(len(boards), 2)
        pairs = boards[0]["meta"]["pairs"]
        self.assertEqual([pair["value"] for pair in pairs], ["19.4-alpha", "296 от ~662", "50"])
        self.assertEqual(pairs[0]["label"], "версия днес",
                         "<b> е стойността, <span> до него — етикетът")

    def test_figure_tone_comes_from_the_class(self):
        pairs = self._of("kpi_group")[1]["meta"]["pairs"]
        self.assertEqual([pair["tone"] for pair in pairs], ["danger", "success"])

    def test_number_with_a_note_is_a_single_figure(self):
        kpis = self._of("kpi")
        self.assertEqual(len(kpis), 1)
        self.assertEqual(kpis[0]["meta"]["number"], "30")
        self.assertIn("дни до замразяването", kpis[0]["meta"]["label"])

    def test_section_number_is_dropped_on_purpose_not_lost(self):
        """Номерът висеше като абзац „02"; сега е kicker, за да го отчете
        покритието като изхвърлен нарочно, а не като изгубен."""
        numbers = [block["text"] for block in self._of("kicker")
                   if block["meta"].get("role") == "section_number"]
        self.assertEqual(numbers, ["01", "02"])
        self.assertFalse([block for block in self._of("paragraph")
                          if block["text"] in ("01", "02")])

    def test_section_subtitle_is_a_section_lead_not_the_post_subtitle(self):
        leads = self._of("standfirst")
        self.assertEqual(len(leads), 2)
        self.assertFalse(leads[0]["meta"].get("section"), "dek под h1 е подзаглавието на статията")
        self.assertTrue(leads[1]["meta"].get("section"))
        self.assertEqual(self.artifact.subtitle, SUBTITLE)

    def test_titled_items_become_cards_with_their_chips(self):
        cards = self._of("cards")
        self.assertEqual(len(cards), 3)
        axes = cards[0]["meta"]["items"]
        self.assertEqual([item["title"] for item in axes], ["Сигурност", "Склад"])
        self.assertEqual(axes[0]["badges"][0]["text"], "пренаписване")
        self.assertIn("<code>ir.model.access</code>", axes[0]["body"])
        self.assertIn("<code>ir.rule</code>", axes[0]["body"], "span.m е име на модел")

    def test_chip_inside_a_heading_becomes_a_badge_not_part_of_the_title(self):
        items = self._of("cards")[1]["meta"]["items"]
        self.assertEqual(items[0]["title"], "Резисторите влязоха")
        self.assertEqual(items[0]["badges"], [{"text": "затворено", "tone": "success"}])
        self.assertIn('<pre class="o_artifact_pre_inline">R003 R016 R017</pre>',
                      items[0]["body"])

    def test_question_rows_unwrap_their_inner_div(self):
        items = self._of("cards")[2]["meta"]["items"]
        self.assertEqual([item["title"] for item in items], ["Обхват", "Срок"])

    def test_numbered_items_are_steps(self):
        steps = self._of("steps")
        self.assertEqual(len(steps), 1)
        items = steps[0]["meta"]["items"]
        self.assertEqual([item["number"] for item in items], ["0", "1"])
        self.assertEqual(items[0]["badges"][0]["text"], "евтино · часове")
        self.assertIn("<strong>Защо:</strong>", items[0]["body"])

    def test_note_class_sets_the_callout_tone(self):
        self.assertEqual([block["meta"]["level"] for block in self._of("callout")],
                         ["key", "warning"])

    def test_table_keeps_colspan_header_rows_and_numeric_alignment(self):
        """Без colspan обединената заглавна клетка разместваше колоните."""
        table = self._of("table")[0]["html"]
        self.assertIn('colspan="2"', table)
        self.assertEqual(table.count("<thead>"), 1)
        self.assertEqual(table.count("<tr>", 0, table.index("</thead>")), 2)
        self.assertIn('<td class="text-end">237</td>', table)
        self.assertIn('<td class="o_artifact_mono">ir.rule</td>', table)

    def test_date_is_not_a_figure(self):
        """Календарът на кампанията излизаше като дванадесет едри числа."""
        source = ("<html><body><div class='cal'>"
                  "<div class='cal-day'><span class='d'>02.09</span><span>старт на кампанията</span></div>"
                  "<div class='cal-day'><span class='d'>03.09</span><span>първа публикация</span></div>"
                  "</div></body></html>")
        _title, blocks = self.parser.parse(source)
        kinds = {block["kind"] for block in blocks}
        self.assertFalse(kinds & {"kpi", "kpi_group"}, blocks)
        self.assertIn("02.09", " ".join(block["text"] for block in blocks))

    def test_register_row_class_is_not_a_callout(self):
        """„trap-row" не е капан — редът на регистъра. Иначе 55 находки
        ставаха 55 жълти карета едно под друго."""
        rows = "".join(
            "<div class='trap-row'><div class='tn'>%02d</div><div class='tt'>"
            "<span class='cat'>конфигуриране</span>Капан номер %d се губи мълчаливо</div>"
            "<div class='tw'>Обяснение на капана.</div></div>" % (index, index)
            for index in range(1, 15))
        _title, blocks = self.parser.parse(
            "<html><body><div class='traps'>%s</div></body></html>" % rows)
        self.assertFalse([block for block in blocks if block["kind"] == "callout"])
        cards = [block for block in blocks if block["kind"] == "cards"]
        self.assertEqual(len(cards), 1, "14 номерирани реда са регистър, не стъпки")
        first = cards[0]["meta"]["items"][0]
        self.assertEqual(first["number"], "01")
        self.assertEqual(first["title"], "Капан номер 1 се губи мълчаливо")
        self.assertEqual(first["badges"][0]["text"], "конфигуриране")

    def test_nested_divs_in_a_callout_are_not_glued(self):
        source = ("<html><body><div class='note'><div>първо изречение</div>"
                  "<div>второ изречение</div></div></body></html>")
        _title, blocks = self.parser.parse(source)
        self.assertEqual(blocks[0]["kind"], "callout")
        self.assertIn("<p>първо изречение</p><p>второ изречение</p>", blocks[0]["html"])

    def test_kpi_with_a_tone_class_stays_a_figure(self):
        """<div class="kpi warn"> е число с предупредителен тон, не каре."""
        # Над 80 знака, както в mcp-warmup: такъв етикет не е за табло, а
        # за самостоятелно число с обяснение
        long_label = ("непушнати комита на клона, които чакат преглед преди следващото "
                      "издание и влизат в него само след зелен CI")
        source = ("<html><body><h2>Състояние</h2><div class='kpis'>"
                  "<div class='kpi warn'><b>3</b><span>%s</span></div>"
                  "<div class='kpi'><b>0</b><span>%s</span></div>"
                  "</div></body></html>" % (long_label, long_label))
        _title, blocks = self.parser.parse(source)
        kpis = [block for block in blocks if block["kind"] == "kpi"]
        self.assertEqual([block["meta"]["number"] for block in kpis], ["3", "0"])
        self.assertEqual(kpis[0]["meta"]["tone"], "warning")
        self.assertFalse([block for block in blocks if block["kind"] == "callout"])

    def test_state_icon_does_not_block_a_card(self):
        """Формата на erpnet-roadmap: <div class="task"><div class="tstate">
        <span class="chip">предстои</span></div><div><h3/><p/></div></div>.
        Заглавието е вложено в съседния контейнер; иконката е празна или
        носи чип. И в двата случая задачите са карти, не заглавия и абзаци."""
        empty = ("<div class='task done'><div class='tstate'></div><div><h3>1.1 Задача</h3>"
                 "<p>Описание на задачата.</p></div></div>")
        chipped = "".join(
            "<div class='task'><div class='tstate'><span class='chip'>предстои</span></div>"
            "<div><h3>1.%d Задача</h3><p>Описание на задачата.</p></div></div>" % index
            for index in range(2, 4))
        source = ("<html><body><h2>Фаза</h2><div class='tasks'>%s%s</div></body></html>"
                  % (empty, chipped))
        _title, blocks = self.parser.parse(source)
        cards = [block for block in blocks if block["kind"] == "cards"]
        self.assertEqual(len(cards), 1)
        items = cards[0]["meta"]["items"]
        self.assertEqual([item["title"] for item in items], ["1.1 Задача", "1.2 Задача", "1.3 Задача"])
        self.assertEqual(items[0]["tone"], "success")
        self.assertEqual(items[1]["badges"], [{"text": "предстои", "tone": ""}])
        self.assertIn("Описание на задачата.", items[1]["body"])

    def test_phase_number_before_the_heading_container_is_dropped(self):
        source = ("<html><body><section><div class='phead'><div class='pnum'>1</div>"
                  "<div><h2>Затваряне на фазата</h2><p>Кратко описание.</p></div></div>"
                  "<p>Текст на фазата.</p></section></body></html>")
        _title, blocks = self.parser.parse(source)
        self.assertFalse([block for block in blocks
                          if block["kind"] == "paragraph" and block["text"] == "1"])
        self.assertEqual([block["text"] for block in blocks if block["kind"] == "kicker"], ["1"])

    def test_subsection_number_is_kept_but_not_glued(self):
        """<h3><span class="h3n">2.1</span>Манифестите…</h3> излизаше
        „2.1Манифестите". Номерът на подраздел е смислен — остава, отделен."""
        source = ("<html><body><h2>Раздел</h2><h3><span class='h3n'>2.1</span>Манифестите</h3>"
                  "<p>Текст.</p></body></html>")
        _title, blocks = self.parser.parse(source)
        headings = [block for block in blocks if block["kind"] == "heading" and block["level"] == 3]
        self.assertEqual(headings[0]["text"], "2.1 Манифестите")

    def test_section_with_headings_is_never_swallowed_as_a_card(self):
        titles = [block["text"] for block in self._of("heading") if block["level"] == 2]
        self.assertEqual(titles, ["Присъдите по осите", "Поправеното", "Ред на действие"])

    # ------------------------------------------------------------------
    # Сглобяването
    # ------------------------------------------------------------------
    def test_every_section_declares_its_snippet_and_the_scope_class(self):
        """Стиловете на модула не бива да излизат извън статията."""
        sections = self.tree.xpath("//section")
        self.assertTrue(sections)
        for section in sections:
            self.assertTrue(section.get("data-snippet"))
            self.assertIn("o_artifact", (section.get("class") or "").split())

    def test_figures_board_is_a_numbers_snippet_with_every_value(self):
        boards = self.tree.xpath("//section[@data-snippet='s_numbers']")
        self.assertEqual(len(boards), 2)
        values = [node.text_content().strip()
                  for node in boards[0].xpath(".//*[contains(@class, 'o_artifact_fig_value')]")]
        self.assertEqual(values, ["19.4-alpha", "296 от ~662", "50"])

    def test_cards_and_steps_render_as_their_own_sections(self):
        self.assertEqual(len(self.tree.xpath("//section[@data-name='Cards']")), 3)
        numbers = [node.text_content().strip()
                   for node in self._by_class("o_artifact_step_number", "span")]
        self.assertEqual(numbers, ["0", "1"])

    def test_chips_are_odoo_badges(self):
        texts = {node.text_content().strip() for node in self._by_class("s_badge", "span")}
        self.assertTrue({"пренаписване", "затворено", "uom_id", "евтино · часове"} <= texts,
                        texts)

    def test_key_note_is_a_highlight_and_the_trap_an_alert(self):
        self.assertEqual(len(self._by_class("s_text_highlight", "div")), 1)
        alerts = self._by_class("s_alert", "div")
        self.assertEqual(len(alerts), 1)
        self.assertIn("alert-warning", alerts[0].get("class"))

    def test_consecutive_details_become_one_accordion(self):
        accordions = self._by_class("s_accordion", "div")
        self.assertEqual(len(accordions), 1)
        buttons = accordions[0].xpath(".//button")
        self.assertEqual(len(buttons), 3)
        targets = [button.get("data-bs-target") for button in buttons]
        self.assertEqual(len(set(targets)), 3, "всеки бутон — свой панел")
        for target in targets:
            self.assertEqual(len(self.tree.xpath("//div[@id='%s']" % target[1:])), 1)

    def test_lead_is_not_repeated_under_the_post_subtitle(self):
        self.assertNotIn("колко струва преходът", self.content)

    def test_structures_carry_every_word(self):
        """Контролното число е върху РЕЗУЛТАТА: структура, която изяжда
        текст, е по-лоша от грозния абзац, който замества."""
        report = self.artifact._coverage_report()
        self.assertEqual(report["missing_words"], 0, report)
