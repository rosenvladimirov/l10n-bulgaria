# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Детерминистичен парсер: самостоятелен Claude артефакт -> плосък списък блокове.

Тук НЯМА нито ред LLM. Артефактът е HTML и структурата му е носителят на
смисъла: h2 значи секция, pre значи код, table значи таблица. Мапването към
Odoo снипети е ОТДЕЛНА стъпка (claude.snippet.rule) — парсерът само казва
какво е видял, не как ще изглежда.
"""

import copy
import logging
import re

from markupsafe import escape

from odoo import api, models

_logger = logging.getLogger(__name__)

try:
    from lxml import etree, html as lxml_html
except ImportError:  # pragma: no cover
    lxml_html = None
    etree = None
    _logger.debug("lxml is not available; artifact parsing is disabled")

# Тагове, които изхвърляме напълно — артефактният CSS/JS не пътува към блога
DROP_TAGS = ("script", "style", "noscript", "template", "link", "meta", "head")

# Inline тагове, които оцеляват вътре в блок; всичко останало се разтваря до текст
KEEP_INLINE = (
    "b", "strong", "i", "em", "u", "s", "code", "kbd", "sub", "sup",
    "a", "br", "span", "small", "mark", "abbr", "del", "ins",
)

# Атрибути, които оцеляват по inline елемент (артефактните class/style — не)
KEEP_ATTRS = {"a": ("href", "title"), "abbr": ("title",), "img": ("src", "alt", "title")}

# Водещ маркер в текста, който прави блока предупреждение вместо параграф.
# Артефактите на Росен са пълни с тези — 🚨 е гоч, ⚠️ е капан, ✅ е закрито.
CALLOUT_MARKERS = {
    "\U0001f6a8": "danger",   # 🚨
    "⚠": "warning",      # ⚠
    "❗": "warning",      # ❗
    "✅": "success",      # ✅
    "ℹ": "info",         # ℹ
    "\U0001f511": "info",     # 🔑
    "\U0001f4cc": "info",     # 📌
}

# Клас/роля, която прави блока предупреждение независимо от текста. Сравнява
# се по ЦЕЛИ класове: регулярният \btrap\b хващаше „trap-row" през тирето и
# регистър от 55 находки ставаше 55 жълти карета едно под друго. По префикс
# минават само общоприетите форми — „alert-danger", „note-warn".
CALLOUT_TOKENS = {"alert", "callout", "warning", "warn", "trap", "danger", "notice",
                  "admonition", "caution", "tip", "note", "info-box", "verdict", "takeaway"}
CALLOUT_PREFIXES = {"alert", "callout", "note", "warning", "danger", "notice",
                    "admonition", "caution", "tip"}

# Клас, с който артефактът номерира секциите си: <h2><span class="num">01</span>
# Заглавие</h2>. Номерът е дизайн, не съдържание — в блога оглавлението си има
# свой ред, а слепен той дава „01Какво се иска" в заглавие, откъс и ключови думи.
HEADING_NUMBER_CLASS_RE = re.compile(r"(?i)\b(num|number|idx|index|counter|step|ord)\b")

# Клас, която издава показател (голямо число) в артефакта
KPI_CLASS_RE = re.compile(r"(?i)\b(kpi|kpis|metric|metrics|stat|stats|big-?number|counter|score|figures)\b")

# Число или процент сам-самичък в елемента — вторият признак за показател
KPI_TEXT_RE = re.compile(r"^[\s]*[+\-]?[\d  .,]+\s*(%|‰|лв\.?|EUR|BGN|GB|MB|s|ms|ч|дни)?\s*$")

# Класове, с които артефактът маркира надзаглавие и водещ абзац — те не са
# текст на статията, а подзаглавие/анотация на блог поста
KICKER_CLASS_RE = re.compile(r"(?i)\b(eyebrow|kicker|overline|suptitle|meta-?line)\b")
STANDFIRST_CLASS_RE = re.compile(r"(?i)\b(standfirst|dek|lede|lead-?in|subtitle|summary|intro)\b")

# Над тази дължина етикетът вече не е етикет на показател, а абзац
KPI_LABEL_MAX = 160

# Над тази дължина стойността в табло не е число за едър шрифт, а текст
FIGURE_VALUE_MAX = 24

# Над тази дължина етикетът до число вече не е етикет на табло
FIGURE_LABEL_MAX = 80

# Класовете по-долу се сравняват като ЦЕЛИ имена, не като подниз: „m-stop"
# не бива да хване „m", а „cost" не е „cos". Изключение е тонът — там
# „m-stop" и „alert-danger" носят оценката в частта след тирето.

# Тонът на елемент по класа му. Артефактите кодират оценката в класа
# („fig bad", „card ok", „note trap") — това е смисъл, не украса, затова
# статията го показва с цвета на темата. Редът е приоритетът.
TONE_TOKENS = (
    ("key", {"key", "verdict", "takeaway", "thesis", "conclusion"}),
    ("danger", {"danger", "bad", "critical", "stop", "error", "fail", "failed", "broken"}),
    ("warning", {"warn", "warning", "trap", "caution", "risk", "high", "attention"}),
    ("success", {"good", "ok", "done", "safe", "success", "pass", "passed", "closed", "fixed"}),
)

# Кратък етикет до текста: става s_badge
CHIP_TOKENS = {"chip", "tag", "pill", "badge", "scale", "cost", "status", "count", "state"}

# Inline име на модел, файл или път: става <code>
MONO_TOKENS = {"m", "mono", "ref", "path", "file", "sha", "hash", "kbd"}

# Блок с доказателство или изход, подреден по редове: става <pre>
PRE_TOKENS = {"proof", "pre", "mono", "code", "out", "output", "trace", "cmd"}

# Клетка с число: подравнява се вдясно, за да се четат разрядите
NUMERIC_CELL_TOKENS = {"num", "n", "amount", "qty", "money", "sum", "right", "r", "num-r"}
CENTERED_CELL_TOKENS = {"num-c", "center", "c"}
DIM_CELL_TOKENS = {"dim", "muted", "faint"}

# Подзаглавие под заглавието на секция: „sec-sub", „dek", „lede"
SUBTITLE_TOKENS = {"sub", "sec-sub", "subtitle", "dek", "deck", "lede", "lead",
                   "standfirst", "summary", "intro"}

# Класове, които казват, че повтарящите се елементи са ПОСЛЕДОВАТЕЛНОСТ
STEP_TOKENS = {"step", "steps", "chain", "stage", "stages", "phase", "phases",
               "timeline", "flow"}

# Номер на секция или стъпка: „01", „4.", „0"
NUMBER_ONLY_RE = re.compile(r"\d{1,3}[.)]?")

# Дата „02.09" или „02.09.2026" не е показател: календарът на кампанията
# излизаше като дванадесет едри числа
DATE_RE = re.compile(r"(\d{2})\.(\d{2})(?:\.(?:\d{2}|\d{4}))?")

# Блокови обвивки, които изчезват от вътрешния HTML на блок
BLOCK_WRAPPERS = ("div", "section", "article", "aside", "header", "footer", "main",
                  "nav", "figure", "details", "summary")

# Тагове, през които елементът вече не е inline текст, а структура
BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "dl", "table",
              "pre", "blockquote", "details", "figure", "svg", "img", "hr", "div",
              "section", "article", "aside", "header", "footer", "nav", "main")

# Елементи, които могат да бъдат карта или стъпка в група
ITEM_TAGS = ("div", "section", "article", "aside", "li")

# Под тази граница елементът е заглавие на карта, над нея — текст.
# Находките в регистрите имат заглавия-изречения до ~140 знака
CARD_TITLE_MAX = 160

# Номерирани елементи до този брой са последователност (стъпки); повече —
# регистър (01…55), където номерът е идентификатор, не ред на действие
STEPS_MAX = 12

# Карта с повече текст от това е подраздел, не карта
CARD_BODY_MAX = 1800

BLOCK_HANDLERS = {
    "h1": "heading", "h2": "heading", "h3": "heading",
    "h4": "heading", "h5": "heading", "h6": "heading",
    "p": "paragraph",
    "ul": "list", "ol": "list",
    "pre": "code",
    "table": "table",
    "blockquote": "quote",
    "hr": "separator",
    "img": "image",
    "svg": "svg",
    "details": "accordion",
    "dl": "definitions",
    "figcaption": "caption",
}

# Контейнери, през които слизаме навътре, вместо да ги емитваме като блок
CONTAINER_TAGS = (
    "div", "section", "article", "main", "aside", "header", "footer",
    "nav", "body", "html", "span", "li", "td", "th", "tr", "tbody", "thead",
)

# Фигурата не е блок, а обвивка: носи изображение И често таблица в <details>
FIGURE_TAGS = ("figure", "picture")


class ClaudeArtifactParser(models.AbstractModel):
    _name = "claude.artifact.parser"
    _description = "Claude Artifact Parser (HTML to blocks)"

    # ------------------------------------------------------------------
    # Публичен вход
    # ------------------------------------------------------------------
    @api.model
    def parse(self, source, source_format="html", known_title=None):
        """Връща (title, blocks) — заглавие и подреден списък от dict-ове.

        Всеки блок: {kind, sequence, level, html, text, lang, anchor, meta}
        known_title е заглавието, което сесията вече е дала: h1, който го
        повтаря, не бива да влиза и в тялото на статията.
        """
        if source_format == "markdown":
            source = self._markdown_to_html(source or "")
        if not (source or "").strip():
            return "", []
        if lxml_html is None:
            raise ImportError("lxml is required to parse Claude artifacts")

        tree = lxml_html.fromstring(source)
        title = self._extract_title(tree)
        # Стиловете на артефакта се изхвърлят, но диаграмите СТЪПВАТ на тях:
        # без тях всяка крива и всеки стълб излизат черни. Носим ги през
        # контекста — BaseModel има __slots__, атрибут върху self не се слага.
        parser = self.with_context(artifact_css=self._collect_css(tree))
        root = parser._content_root(tree)
        blocks = []
        # Коренът също може да е структура: артефакт, чието тяло е едно каре
        # или един регистър, иначе губеше формата си — обхождането слизаше
        # в него като в обвивка
        if not parser._walk_structure(root, blocks):
            parser._walk(root, blocks)
        blocks = parser._post_process(blocks, title, known_title)
        for index, block in enumerate(blocks, start=1):
            block["sequence"] = index * 10
        return title, blocks

    # ------------------------------------------------------------------
    # Заглавие и корен на съдържанието
    # ------------------------------------------------------------------
    @api.model
    def _extract_title(self, tree):
        for xpath in ("//head/title/text()", "//h1[1]//text()"):
            found = tree.xpath(xpath)
            if found:
                title = " ".join(t.strip() for t in found if t.strip())
                if title:
                    return re.sub(r"\s+", " ", title).strip()
        return ""

    @api.model
    def _content_root(self, tree):
        """Слиза през обвивките на артефакта до елемента, който носи съдържанието.

        Артефактите обикновено са <body><div class="wrap"><main>…, а всяка
        обвивка носи собствен CSS, който тук не значи нищо.
        """
        for tag in DROP_TAGS:
            for node in tree.xpath("//%s" % tag):
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
        if etree is not None:
            for comment in tree.xpath("//comment()"):
                parent = comment.getparent()
                if parent is not None:
                    parent.remove(comment)

        root = tree.find("body")
        if root is None:
            root = tree
        while True:
            children = [child for child in root if isinstance(child.tag, str)]
            own_text = (root.text or "").strip()
            if len(children) == 1 and not own_text and children[0].tag in CONTAINER_TAGS:
                root = children[0]
                continue
            return root

    # ------------------------------------------------------------------
    # Обхождане
    # ------------------------------------------------------------------
    @api.model
    def _walk(self, node, blocks):
        text_before = (node.text or "").strip()
        if text_before and node.tag in CONTAINER_TAGS:
            blocks.append(self._make_block("paragraph", html="<p>%s</p>" % text_before,
                                           text=text_before))
        for child in node:
            if not isinstance(child.tag, str):
                continue
            tag = etree.QName(child).localname.lower() if ":" in str(child.tag) else child.tag.lower()
            if tag in DROP_TAGS:
                continue
            kind = BLOCK_HANDLERS.get(tag)
            if self._is_section_number(child):
                # Номерът на секцията е дизайн — блогът има свое оглавление.
                # Става kicker, за да го отчете покритието като НАРОЧНО
                # изхвърлен, а не като изгубен текст.
                blocks.append(self._make_block(
                    "kicker", text=self._plain_text(child),
                    meta={"role": "section_number"}))
            elif tag in FIGURE_TAGS:
                self._walk_figure(child, blocks)
            elif kind:
                block = self._build(kind, child, tag)
                if block:
                    blocks.append(block)
                elif [grand for grand in child if isinstance(grand.tag, str)]:
                    # Билдърът не разпозна нищо, но вътре ИМА съдържание —
                    # слизаме, вместо да го изядем тихо (намерено: <details>
                    # с таблица, скрит вътре в <figure>)
                    self._walk(child, blocks)
            elif tag in CONTAINER_TAGS:
                if not self._walk_structure(child, blocks):
                    self._walk(child, blocks)
            else:
                text = self._plain_text(child)
                if text:
                    blocks.append(self._make_block(
                        "paragraph", html="<p>%s</p>" % self._inner_html(child), text=text))
            tail = (child.tail or "").strip()
            if tail:
                blocks.append(self._make_block("paragraph", html="<p>%s</p>" % tail, text=tail))

    @api.model
    def _build(self, kind, node, tag):
        builder = getattr(self, "_build_%s" % kind, None)
        if builder is None:
            return None
        return builder(node, tag)

    # ------------------------------------------------------------------
    # Структури: контейнер, чиято форма носи смисъл (ADR-0004)
    # ------------------------------------------------------------------
    @api.model
    def _walk_structure(self, node, blocks):
        """Контейнер, чиято СТРУКТУРА носи смисъл, става един блок.

        Досега всеки div, който не е предупреждение или показател, се
        разтваряше: таблото „етикет/число" ставаше редуващи се абзаци, а
        картата — заглавие, чип и текст един под друг, без връзка помежду им.
        Разпознаването е по формата, не по имената на класовете: повтарящи
        се еднакви елементи са група, каквито и класове да носят.
        Връща True, ако контейнерът е поет; иначе обхождането слиза в него.
        """
        if self._walk_section_head(node, blocks):
            return True
        # Показателят, обявен с клас, бие тона: <div class="kpi warn"> е
        # число с предупредителен тон, не каре с текст „3 непушнати комита"
        if KPI_CLASS_RE.search(node.get("class") or ""):
            kpi = self._detect_kpi(node)
            if kpi:
                blocks.append(kpi)
                return True
        declared = self._detect_callout(node, by_class_only=True)
        if declared and self._plain_text(node):
            blocks.append(self._callout_block(node, declared))
            return True
        for detector in (self._detect_figures, self._detect_items):
            block = detector(node)
            if block:
                blocks.append(block)
                return True
        # Маркерът (🚨 ⚠️ ✅) прави предупреждение само от контейнер без
        # заглавия — иначе цял раздел, започващ с ⚠️, ставаше едно каре
        marked = self._marker_level(self._plain_text(node))
        if marked and not node.xpath(".//h1|.//h2|.//h3"):
            blocks.append(self._callout_block(node, marked))
            return True
        for detector in (self._detect_number_note, self._detect_inline_run):
            block = detector(node)
            if block:
                blocks.append(block)
                return True
        return False

    @api.model
    def _callout_block(self, node, level):
        # Блоковите тагове остават: предупреждение с два абзаца и списък
        # иначе излизаше слепено в един ред
        return self._make_block("callout", html=self._inner_html(node, allow_blocks=True),
                                text=self._plain_text(node), meta={"level": level})

    @api.model
    def _is_section_number(self, node):
        """Самостоятелен номер („02") точно преди заглавие е номер на секция."""
        if node.tag in ("h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "pre"):
            return False
        if not NUMBER_ONLY_RE.fullmatch(self._plain_text(node)):
            return False
        if [child for child in node if isinstance(child.tag, str)
                and child.tag not in KEEP_INLINE]:
            return False
        following = node.getnext()
        while following is not None and not isinstance(following.tag, str):
            following = following.getnext()
        if following is None:
            return False
        if following.tag in ("h1", "h2", "h3"):
            return True
        # <div class="pnum">1</div><div><h2>Фаза</h2>…</div>: заглавието е
        # първото нещо в съседния контейнер
        first = next((child for child in following if isinstance(child.tag, str)), None)
        return (following.tag in CONTAINER_TAGS and first is not None
                and first.tag in ("h1", "h2", "h3") and not (following.text or "").strip())

    @api.model
    def _walk_section_head(self, node, blocks):
        """Глава на секция: номер, заглавие и подзаглавие в обща обвивка.

        Артефактите пишат <div class="sec-head"><div class="sec-num">02</div>
        <h2>…</h2><p class="sec-sub">…</p></div>. Номерът висеше като самотен
        абзац „02" над заглавието, а подзаглавието — като обикновен текст.
        """
        children = [child for child in node if isinstance(child.tag, str)]
        if not 2 <= len(children) <= 4 or (node.text or "").strip():
            return False
        if any((child.tail or "").strip() for child in children):
            return False
        headings = [child for child in children if child.tag in ("h1", "h2", "h3")]
        if len(headings) != 1:
            return False
        position = children.index(headings[0])
        number = ""
        subtitles = []
        for index, child in enumerate(children):
            if index == position:
                continue
            text = self._plain_text(child)
            if index < position and not number and NUMBER_ONLY_RE.fullmatch(text):
                number = text
            elif (index > position and text and self._class_tokens(child) & SUBTITLE_TOKENS
                  and not child.xpath(".//table|.//ul|.//ol|.//pre")):
                subtitles.append(child)
            else:
                return False
        heading = self._build_heading(headings[0], headings[0].tag)
        if not heading:
            return False
        if number:
            blocks.append(self._make_block("kicker", text=number,
                                           meta={"role": "section_number"}))
        blocks.append(heading)
        # Подзаглавието на РАЗДЕЛ не е подзаглавие на статията: флагът пази
        # action_parse да не го вземе за subtitle на поста. Под h1 то е
        # точно подзаглавието на статията и флаг няма.
        meta = {"section": True} if headings[0].tag != "h1" else {}
        for sub in subtitles:
            blocks.append(self._make_block(
                "standfirst", html="<p>%s</p>" % self._inner_html(sub),
                text=self._plain_text(sub), meta=dict(meta)))
        return True

    @api.model
    def _detect_figures(self, node):
        """Табло: повтарящи се двойки „стойност + етикет".

        Артефактите пишат таблото по много начини — <div class="mm"><span>
        етикет</span><b>стойност</b></div>, <div class="fig bad"><span
        class="n">24</span><span class="l">…</span></div>, <div class="metric">
        <b>10</b><span>…</span></div>. Общото е формата: всеки елемент е къса
        стойност и кратък етикет. Разпаднато, то даваше редуващи се абзаци.
        """
        items = [child for child in node if isinstance(child.tag, str)]
        if not 2 <= len(items) <= 12 or (node.text or "").strip():
            return None
        pairs = []
        for item in items:
            if (item.tail or "").strip():
                return None
            pair = self._figure_pair(item)
            if not pair:
                return None
            pairs.append(pair)
        text = " · ".join(
            " ".join(filter(None, [pair["value"], pair["label"], pair["note"]]))
            for pair in pairs
        )
        markup = "".join("<dt>%s</dt><dd>%s</dd>" % (escape(pair["label"]), escape(pair["value"]))
                         for pair in pairs)
        return self._make_block("kpi_group", html="<dl>%s</dl>" % markup, text=text,
                                meta={"pairs": pairs, "count": len(pairs)})

    @api.model
    def _figure_pair(self, item):
        if item.tag not in ("div", "span", "li", "section", "article") or (item.text or "").strip():
            return None
        parts = [child for child in item if isinstance(child.tag, str)]
        if not 2 <= len(parts) <= 3:
            return None
        for part in parts:
            if part.tag in BLOCK_TAGS and part.tag not in ("div", "p"):
                return None
            if any(isinstance(inner.tag, str) and inner.tag in BLOCK_TAGS
                   for inner in part.iterdescendants()):
                return None
            if (part.tail or "").strip():
                return None
        texts = [self._plain_text(part) for part in parts]
        if not all(texts):
            return None
        # Първо числото, после удебеленото или класът: <b>Срок:</b><span>30
        # дни</span> иначе обръща етикета и стойността
        value_index = None
        for index, text in enumerate(texts):
            if (len(text) <= FIGURE_VALUE_MAX and KPI_TEXT_RE.match(text)
                    and not self._looks_like_date(text)):
                value_index = index
                break
        if value_index is None:
            for index, (part, text) in enumerate(zip(parts, texts)):
                if len(text) <= FIGURE_VALUE_MAX and not self._looks_like_date(text) and (
                        part.tag in ("b", "strong")
                        or self._class_tokens(part) & {"n", "num", "value", "val", "v",
                                                       "number", "big"}):
                    value_index = index
                    break
        if value_index is None:
            return None
        rest = [text for index, text in enumerate(texts) if index != value_index]
        label, note = rest[0], " ".join(rest[1:])
        # Етикетът на табло е кратък. Дълъг текст до номер е ред от регистър
        # („01 · Формула, написана директно…"), където номерът е идентификатор
        if len(label) > FIGURE_LABEL_MAX or len(note) > FIGURE_LABEL_MAX:
            return None
        return {"value": texts[value_index], "label": label, "note": note,
                "tone": self._tone_of(item, allow_key=False)}

    @api.model
    def _detect_items(self, node):
        """Карти и стъпки: повтарящи се елементи със заглавие и текст.

        <div class="axes"><div class="axis"><div class="an">Сигурност</div>
        <span class="scale">пренаписване</span><p>…</p></div>…</div> е ГРУПА:
        заглавие, чип и текст на всеки елемент. С номер или клас step/chain
        групата е последователност и става стъпки.
        """
        # Разпознаването вади чиповете от заглавията — работим върху копие,
        # за да не пипнем дървото, ако накрая се откажем
        clone = copy.deepcopy(node)
        items = [child for child in clone if isinstance(child.tag, str)]
        if not 2 <= len(items) <= 24 or (clone.text or "").strip():
            return None
        entries = []
        for item in items:
            if item.tag not in ITEM_TAGS or (item.tail or "").strip():
                return None
            entry = self._card_item(item)
            if not entry:
                return None
            entries.append(entry)
        if sum(1 for entry in entries if entry["body"]) * 2 < len(entries):
            return None
        tokens = self._class_tokens(clone)
        for item in items:
            tokens |= self._class_tokens(item)
        numbered = all(entry["number"] for entry in entries)
        kind = "steps" if tokens & STEP_TOKENS or (numbered and len(entries) <= STEPS_MAX) \
            else "cards"
        text = " ".join(
            " ".join(filter(None, [entry["number"], entry["title"],
                                   " ".join(badge["text"] for badge in entry["badges"]),
                                   entry.pop("text")]))
            for entry in entries
        )
        wrapper = "ol" if kind == "steps" else "ul"
        markup = "".join("<li><strong>%s</strong> %s</li>" % (escape(entry["title"]), entry["body"])
                         for entry in entries)
        return self._make_block(kind, html="<%s>%s</%s>" % (wrapper, markup, wrapper),
                                text=text, meta={"items": entries, "count": len(entries)})

    @api.model
    def _card_item(self, item):
        children = [child for child in item if isinstance(child.tag, str)]
        own_text = (item.text or "").strip()
        meaningful = [child for child in children if self._plain_text(child)
                      or child.xpath("descendant-or-self::img|descendant-or-self::svg")]
        if (len(meaningful) == 1 and not own_text
                and meaningful[0].tag in ("div", "section", "article")
                and not any((child.tail or "").strip() for child in children)):
            # <div class="q"><div><b>Обхват</b><span>…</span></div></div>, или
            # <div class="task done"><div class="tstate"></div><div><h3/><p/></div>
            # — празната иконка на състоянието не пречи да влезем навътре,
            # а тонът ѝ (или на обвивката) остава на картата
            entry = self._card_item(meaningful[0])
            if entry and not entry["tone"]:
                entry["tone"] = self._tone_of(item, allow_key=False) or next(
                    (self._tone_of(child, allow_key=False) for child in children
                     if child not in meaningful and self._tone_of(child, allow_key=False)), "")
            return entry
        if not children or own_text or item.xpath(".//h1|.//h2"):
            return None
        # Обявеният показател не е карта: <div class="kpi"><b>3</b><span>…</span>
        # иначе ставаше ред от тефтер с „3" за заглавие
        if KPI_CLASS_RE.search(item.get("class") or "") and self._detect_kpi(item):
            return None
        number = title = ""
        badges, body = [], []
        for child in children:
            if (child.tail or "").strip():
                return None
            text = self._plain_text(child)
            if not text and not child.xpath("descendant-or-self::img|descendant-or-self::svg"):
                continue
            tokens = self._class_tokens(child)
            leaf = not any(isinstance(inner.tag, str) and inner.tag in BLOCK_TAGS
                           for inner in child.iterdescendants())
            if not (number or title or badges or body) and leaf and NUMBER_ONLY_RE.fullmatch(text):
                number = text.rstrip(".)")
            elif not title and not body and child.tag in ("h3", "h4", "h5", "h6"):
                self._pull_chips(child, badges)
                title = self._plain_text(child)
            elif not title and not body and self._first_heading(child) is not None:
                # <div class="task"><div class="tstate"><span class="chip">предстои
                # </span></div><div><h3>1.1 …</h3><p>…</p></div></div>: заглавието
                # е вложено в съседния контейнер, а останалото там е тялото
                heading = self._first_heading(child)
                inner_parts = [inner for inner in child if isinstance(inner.tag, str)]
                if any((inner.tail or "").strip() for inner in inner_parts):
                    return None
                self._pull_chips(heading, badges)
                title = self._plain_text(heading)
                body.extend(inner for inner in inner_parts if inner is not heading)
            elif not body and leaf and tokens & CHIP_TOKENS and len(text) <= 60:
                badges.append({"text": self._spaced_text(child),
                               "tone": self._tone_of(child, allow_key=False)})
            elif (not title and not body and leaf
                  and child.tag in ("div", "span", "b", "strong", "p", "dt", "header")
                  and len(self._plain_text(child)) <= CARD_TITLE_MAX + 60):
                # <div class="tt"><span class="cat">конфигуриране</span>Формула…</div>:
                # категорията е чип, не начало на заглавието. Работим върху
                # копие (виж _detect_items), затова изваждането е безопасно.
                self._pull_chips(child, badges)
                text = self._plain_text(child)
                if text and len(text) <= CARD_TITLE_MAX:
                    title = text
                elif text:
                    body.append(child)
            else:
                body.append(child)
        if not title:
            return None
        body_text = " ".join(self._plain_text(part) for part in body)
        # Таблица или много текст значи подраздел, не карта
        if len(body_text) > CARD_BODY_MAX or any(
                part.xpath("descendant-or-self::table") for part in body):
            return None
        return {
            "number": number,
            "title": title,
            "badges": badges,
            "body": "".join(self._fragment_html(part) for part in body),
            "tone": self._tone_of(item, allow_key=False),
            "text": body_text,
        }

    @api.model
    def _first_heading(self, node):
        """Заглавие h3…h6, което е ПЪРВОТО нещо в контейнер, иначе None."""
        if node.tag not in ("div", "section", "article", "header") or (node.text or "").strip():
            return None
        first = next((child for child in node if isinstance(child.tag, str)), None)
        return first if first is not None and first.tag in ("h3", "h4", "h5", "h6") else None

    @api.model
    def _pull_chips(self, node, badges):
        """Вади чиповете от заглавие в списъка със значки."""
        for chip in node.xpath(".//span|.//small"):
            text = self._spaced_text(chip)
            if text and len(text) <= 60 and (
                    self._class_tokens(chip) & (CHIP_TOKENS | {"cat", "category", "kind", "type"})):
                badges.append({"text": text, "tone": self._tone_of(chip, allow_key=False)})
                chip.drop_tree()

    @api.model
    def _spaced_text(self, node):
        """Текстът на чип с интервал между възлите.

        Съставният чип <div class="badge"><span>T0</span><span>constraint
        </span></div> иначе излизаше „T0constraint" — и в статията, и в
        отчета за покритие като две изгубени думи.
        """
        return re.sub(r"\s+", " ", " ".join(node.itertext())).strip()

    @api.model
    def _fragment_html(self, part):
        """Частта от тялото на карта като блоков HTML."""
        if part.tag in ("div", "p", "span") and self._class_tokens(part) & PRE_TOKENS:
            return '<pre class="o_artifact_pre_inline">%s</pre>' % escape(
                part.text_content().strip())
        holder = lxml_html.fromstring("<div></div>")
        clone = copy.deepcopy(part)
        clone.tail = None
        holder.append(clone)
        inner = self._inner_html(holder, allow_blocks=True)
        if not re.search(r"<(p|ul|ol|table|pre|blockquote|dl|h[3-6])\b", inner):
            inner = "<p>%s</p>" % inner
        return inner

    @api.model
    def _detect_inline_run(self, node):
        """Контейнер само с inline съдържание е ЕДИН абзац.

        Иначе <div><b>Меню:</b> текст <code>x</code></div> се режеше на три
        абзаца — удебеленото, текстът и кодът, всеки на свой ред.
        """
        if any(isinstance(inner.tag, str) and inner.tag not in KEEP_INLINE
               for inner in node.iterdescendants()):
            return None
        text = self._plain_text(node)
        if not text:
            return None
        return self._make_block("paragraph", html="<p>%s</p>" % self._inner_html(node),
                                text=text)

    @api.model
    def _detect_number_note(self, node):
        """Число с обяснение: <div><span class="num">30</span><p>дни до …</p></div>."""
        parts = [child for child in node if isinstance(child.tag, str)]
        if len(parts) != 2 or (node.text or "").strip() \
                or any((part.tail or "").strip() for part in parts):
            return None
        number, label = self._plain_text(parts[0]), self._plain_text(parts[1])
        if not (number and label) or len(number) > 8 or not re.search(r"\d", number) \
                or not KPI_TEXT_RE.match(number) or self._looks_like_date(number):
            return None
        if parts[1].tag not in ("p", "div", "span") or len(label) > 240:
            return None
        if any(isinstance(inner.tag, str) and inner.tag in BLOCK_TAGS
               for inner in parts[1].iterdescendants()):
            return None
        return self._make_block("kpi", html="", text="%s %s" % (number, label),
                                meta={"number": number, "label": label})

    @api.model
    def _class_tokens(self, node):
        return set((node.get("class") or "").lower().split())

    @api.model
    def _looks_like_date(self, text):
        match = DATE_RE.fullmatch((text or "").strip())
        return bool(match) and 1 <= int(match.group(1)) <= 31 and 1 <= int(match.group(2)) <= 12

    @api.model
    def _tone_of(self, node, allow_key=True):
        """Тонът по класа: цели имена плюс частите след тирето („m-stop")."""
        tokens = set()
        for token in (node.get("class") or "").lower().split():
            tokens.add(token)
            tokens.update(part for part in token.split("-") if part)
        for tone, names in TONE_TOKENS:
            if tone == "key" and not allow_key:
                continue
            if tokens & names:
                return tone
        return ""

    @api.model
    def _chip_class(self, node):
        tone = self._tone_of(node, allow_key=False)
        # Без класа .badge: темата на Odoo 19 го облича с border: 0 и плътен
        # фон, който бие правилата на модула. s_badge стига на редактора.
        return "s_badge o_artifact_chip%s" % (" o_artifact_tone_%s" % tone if tone else "")

    @api.model
    def _cell_attrs(self, cell):
        """colspan/rowspan и подравняването оцеляват; останалото — не.

        Без colspan таблица с обединена заглавна клетка разместваше всички
        колони под нея.
        """
        attrs = []
        for name in ("colspan", "rowspan"):
            value = (cell.get(name) or "").strip()
            if value.isdigit() and int(value) > 1:
                attrs.append(' %s="%s"' % (name, value))
        tokens = self._class_tokens(cell)
        classes = []
        if tokens & NUMERIC_CELL_TOKENS:
            classes.append("text-end")
        elif tokens & CENTERED_CELL_TOKENS:
            classes.append("text-center")
        if tokens & MONO_TOKENS:
            classes.append("o_artifact_mono")
        if tokens & DIM_CELL_TOKENS:
            classes.append("text-muted")
        if classes:
            attrs.append(' class="%s"' % " ".join(classes))
        return "".join(attrs)

    # ------------------------------------------------------------------
    # Блокове по вид
    # ------------------------------------------------------------------
    @api.model
    def _build_heading(self, node, tag):
        self._drop_heading_number(node)
        self._space_heading_number(node)
        text = self._plain_text(node)
        if not text:
            return None
        level = int(tag[1])
        return self._make_block(
            "heading",
            html="<h%d>%s</h%d>" % (level, self._inner_html(node), level),
            text=text,
            level=level,
            anchor=self._slugify(text),
        )

    @api.model
    def _drop_heading_number(self, node):
        """Маха водещия номер на секцията от заглавието.

        Артефактите пишат <h2><span class="num">01</span>Заглавие</h2>; без
        това текстът излиза „01Заглавие" — слепен, защото между двата възела
        няма интервал — и тръгва така в статията, в откъса и в ключовите думи.
        """
        children = [child for child in node if isinstance(child.tag, str)]
        if not children:
            return
        first = children[0]
        if (node.text or "").strip():
            return
        if not HEADING_NUMBER_CLASS_RE.search(first.get("class") or ""):
            return
        if not re.fullmatch(r"[\s\d.)\-–—]{1,8}", first.text_content() or ""):
            return
        tail = first.tail or ""
        node.remove(first)
        node.text = ((node.text or "") + tail).lstrip(" .)-–—")

    @api.model
    def _space_heading_number(self, node):
        """Номерът на подраздел остава, но не слепен: „2.1 Манифестните…".

        <h3><span class="h3n">2.1</span>Манифестните…</h3> — класът не е от
        номерните, затова _drop_heading_number не го пипа, а между двата
        възела няма интервал. При h3 номерът е смислен (2.1 спрямо раздел 2),
        затова не се маха — само се отделя.
        """
        if (node.text or "").strip():
            return
        first = next((child for child in node if isinstance(child.tag, str)), None)
        if first is None or first.tag not in ("span", "b", "strong", "small"):
            return
        if not re.fullmatch(r"\d{1,3}(\.\d{1,3})*[.)]?", (first.text_content() or "").strip()):
            return
        if not (first.tail or "").startswith((" ", " ")):
            first.tail = " " + (first.tail or "")

    @api.model
    def _build_paragraph(self, node, tag):
        text = self._plain_text(node)
        if not text:
            return None
        blob = node.get("class") or ""
        if KICKER_CLASS_RE.search(blob):
            return self._make_block("kicker", html="", text=text)
        if STANDFIRST_CLASS_RE.search(blob):
            return self._make_block("standfirst", html="<p>%s</p>" % self._inner_html(node),
                                    text=text)
        callout = self._detect_callout(node) or self._marker_level(text)
        if callout:
            return self._make_block("callout", html=self._inner_html(node), text=text,
                                    meta={"level": callout})
        return self._make_block("paragraph", html="<p>%s</p>" % self._inner_html(node),
                                text=text)

    @api.model
    def _build_list(self, node, tag):
        items = []
        for item in node.xpath("./li|./dt|./dd"):
            inner = self._inner_html(item, allow_blocks=True)
            if inner.strip():
                items.append("<li>%s</li>" % inner)
        if not items:
            return None
        wrapper = "ol" if tag == "ol" else "ul"
        return self._make_block(
            "list",
            html="<%s>%s</%s>" % (wrapper, "".join(items), wrapper),
            text=self._plain_text(node),
            meta={"ordered": tag == "ol", "items": len(items)},
        )

    @api.model
    def _build_definitions(self, node, tag):
        """<dl> е двойки етикет/стойност; при клас stat/kpi става табло с числа.

        Артефактите пишат таблото като <dl class="stat"><div><dt>етикет</dt>
        <dd>число<small>бележка</small></dd></div>…</dl> — обвиващият <div>
        изяждаше цялата двойка, защото xpath-ът гледаше само преки деца.
        """
        pairs = []
        terms = node.xpath(".//dt")
        for term in terms:
            label = self._plain_text(term)
            value = note = ""
            definition = term.getnext()
            if definition is None or definition.tag != "dd":
                holder = term.getparent()
                candidates = holder.xpath("./dd") if holder is not None else []
                definition = candidates[0] if candidates else None
            if definition is not None:
                small = definition.xpath("./small|./span[@class='note']")
                if small:
                    note = self._plain_text(small[0])
                    small[0].getparent().remove(small[0])
                value = self._plain_text(definition)
            if label or value:
                pairs.append({"label": label, "value": value, "note": note})
        if not pairs:
            return None
        blob = node.get("class") or ""
        kind = "kpi_group" if KPI_CLASS_RE.search(blob) else "definitions"
        text = " · ".join(
            " ".join(filter(None, [pair["value"], pair["label"], pair["note"]]))
            for pair in pairs
        )
        items = "".join(
            "<dt>%s</dt><dd>%s</dd>" % (
                pair["label"],
                " ".join(filter(None, [pair["value"],
                                       "<small>%s</small>" % pair["note"] if pair["note"] else ""])),
            )
            for pair in pairs
        )
        return self._make_block(kind, html="<dl>%s</dl>" % items, text=text,
                                meta={"pairs": pairs, "count": len(pairs)})

    @api.model
    def _build_code(self, node, tag):
        code_node = node.find("code")
        target = code_node if code_node is not None else node
        code = target.text_content()
        if not code.strip():
            return None
        lang = ""
        for attr in (target.get("class") or "", node.get("class") or ""):
            match = re.search(r"(?:language|lang)-([\w+#.-]+)", attr)
            if match:
                lang = match.group(1)
                break
            if attr.strip() and not lang and re.fullmatch(r"[\w+#.-]+", attr.strip()):
                lang = attr.strip()
        return self._make_block("code", html="", text=code.rstrip(), lang=lang)

    @api.model
    def _build_table(self, node, tag):
        head, body = [], []
        has_thead = bool(node.xpath("./thead"))
        for row in node.xpath(".//tr"):
            raw_cells = row.xpath("./th|./td")
            cells = []
            for cell in raw_cells:
                cell_tag = "th" if cell.tag == "th" else "td"
                cells.append("<%s%s>%s</%s>" % (
                    cell_tag, self._cell_attrs(cell), self._inner_html(cell), cell_tag))
            if not cells:
                continue
            parent = row.getparent()
            # Заглавният ред отива в <thead>: темата го оформя като заглавие,
            # а не като поредния ред с удебелен текст
            in_head = (parent is not None and parent.tag == "thead") or (
                not has_thead and not body and all(cell.tag == "th" for cell in raw_cells))
            (head if in_head else body).append("<tr>%s</tr>" % "".join(cells))
        if not (head or body):
            return None
        rows = head + body
        markup = ("<thead>%s</thead>" % "".join(head) if head else "") + (
            "<tbody>%s</tbody>" % "".join(body) if body else "")
        caption = node.xpath("./caption//text()")
        return self._make_block(
            "table",
            html=markup,
            text=" ".join(node.text_content().split())[:512],
            meta={
                "rows": len(rows),
                "caption": " ".join(c.strip() for c in caption if c.strip()),
                "header": bool(node.xpath(".//th")),
            },
        )

    @api.model
    def _build_quote(self, node, tag):
        text = self._plain_text(node)
        if not text:
            return None
        cite = node.xpath(".//cite//text()|.//footer//text()")
        return self._make_block("quote", html=self._inner_html(node), text=text,
                                meta={"cite": " ".join(c.strip() for c in cite if c.strip())})

    @api.model
    def _build_separator(self, node, tag):
        return self._make_block("separator", html="", text="")

    @api.model
    def _build_image(self, node, tag):
        src = node.get("src") or ""
        if not src:
            return None
        return self._make_block("image", html="", text=node.get("alt") or "",
                                meta={"src": src, "alt": node.get("alt") or ""})

    @api.model
    def _collect_css(self, tree):
        """Събира текста на всички <style> в артефакта, преди да ги изхвърлим."""
        chunks = [node.text_content() for node in tree.xpath("//style")]
        return "\n".join(chunk for chunk in chunks if (chunk or "").strip())

    @api.model
    def _css_variables(self, css):
        """Стойностите от първия :root блок — светлата тема на артефакта."""
        match = re.search(r":root\s*\{([^{}]*)\}", css)
        if not match:
            return {}
        variables = {}
        for declaration in match.group(1).split(";"):
            if ":" not in declaration:
                continue
            name, _, value = declaration.partition(":")
            name, value = name.strip(), value.strip()
            if name.startswith("--") and value:
                variables[name] = value
        return variables

    @api.model
    def _resolve_vars(self, value, variables, depth=0):
        """Заменя var(--x) със стойността; fallback-ът след запетая се пази."""
        if "var(" not in value or depth > 4:
            return value

        def swap(match):
            name = match.group(1).strip()
            fallback = (match.group(2) or "").strip(" ,")
            return variables.get(name, fallback)

        resolved = re.sub(r"var\(\s*(--[\w-]+)\s*(,[^()]*)?\)", swap, value)
        return self._resolve_vars(resolved, variables, depth + 1)

    @api.model
    def _style_svg_inline(self, node):
        """Пренася стиловете на артефакта ВЪРХУ елементите на диаграмата.

        Вграден <style> вътре в inline SVG НЕ е ограничен до него — в HTML
        документ той важи за цялата страница и би пребоядисал сайта. Затова
        декларациите слизат като style атрибути, с разрешени променливи.
        Без това всяка крива и всеки стълб излизат черни: правилата стоят на
        `.chart .bar`, а обвивката `.chart` не пътува към статията.
        """
        css = self.env.context.get("artifact_css") or ""
        if not css.strip():
            return False
        variables = self._css_variables(css)
        rules = []
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            selector, body = match.group(1).strip(), match.group(2).strip()
            if not body or selector.startswith("@") or ":root" in selector:
                continue
            for single in selector.split(","):
                single = single.strip()
                if not single:
                    continue
                last = re.split(r"[\s>+~]+", single)[-1]
                if ":" in last:          # псевдокласове не се инлайнват
                    continue
                tag = re.match(r"^[\w-]+", last)
                classes = set(re.findall(r"\.([\w-]+)", last))
                if not tag and not classes:
                    continue
                rules.append((tag.group(0).lower() if tag else None, classes, body))
        if not rules:
            return False

        touched = False
        for element in node.iter():
            if not isinstance(element.tag, str):
                continue
            name = (etree.QName(element).localname.lower()
                    if "}" in str(element.tag) else element.tag.lower())
            own = set((element.get("class") or "").split())
            collected = []
            for tag, classes, body in rules:
                if tag and tag != name:
                    continue
                if classes and not classes.issubset(own):
                    continue
                if not tag and not classes:
                    continue
                collected.append(self._resolve_vars(body, variables))
            if not collected:
                continue
            # Собственият style на елемента бие правилата, затова е последен
            existing = (element.get("style") or "").strip()
            merged = "; ".join(part.strip().rstrip(";") for part
                               in collected + [existing] if part.strip())
            element.set("style", merged)
            touched = True
        return touched

    @api.model
    def _build_svg(self, node, tag):
        styled = self._style_svg_inline(node)
        markup = etree.tostring(node, encoding="unicode", with_tail=False)
        return self._make_block("svg", html=markup, text=self._plain_text(node),
                                meta={"inline": True, "styled": styled})

    @api.model
    def _walk_figure(self, node, blocks):
        """Изображението на фигурата става блок, а останалото ѝ съдържание — свои.

        Артефактите крият таблицата на серията в <details> вътре във фигурата
        до диаграмата. Ако вземем само първото изображение, таблицата отива в
        нищото — тихо.
        """
        captions = node.xpath("./figcaption")
        caption_text = " ".join(filter(None, (self._plain_text(c) for c in captions)))
        visual = node.xpath(".//svg|.//img")
        consumed = set()
        if visual:
            first = visual[0]
            tag = first.tag.lower() if isinstance(first.tag, str) else ""
            block = self._build_svg(first, "svg") if tag == "svg" \
                else self._build_image(first, "img")
            if block:
                block["meta"]["caption"] = caption_text
                block["text"] = " ".join(filter(None, [block["text"], caption_text]))
                blocks.append(block)
                consumed.add(first)
                for element in first.iter():
                    consumed.add(element)
        for caption in captions:
            consumed.add(caption)
            for element in caption.iter():
                consumed.add(element)
        # Обхождаме останалото: клонираме фигурата без изконсумираните части,
        # за да не пипаме дървото, което още се мери отвън
        leftovers = [child for child in node
                     if isinstance(child.tag, str) and child not in consumed
                     and not any(descendant in consumed for descendant in child.iter())]
        for child in leftovers:
            holder = lxml_html.fromstring("<div></div>")
            holder.append(lxml_html.fromstring(etree.tostring(child, encoding="unicode", with_tail=False)))
            self._walk(holder, blocks)
        if not visual and not leftovers and caption_text:
            blocks.append(self._make_block("caption", html="<p>%s</p>" % caption_text,
                                           text=caption_text))

    @api.model
    def _build_accordion(self, node, tag):
        summary = node.xpath("./summary")
        head = self._plain_text(summary[0]) if summary else ""
        if summary:
            node.remove(summary[0])
        body = self._inner_html(node, allow_blocks=True)
        if not (head or body.strip()):
            return None
        return self._make_block("accordion", html=body, text=head, meta={"summary": head})

    # ------------------------------------------------------------------
    # Разпознавания
    # ------------------------------------------------------------------
    @api.model
    def _declares_callout(self, node):
        if node.get("role") == "alert":
            return True
        blob = "%s %s" % (node.get("class") or "", node.get("data-name") or "")
        for token in blob.lower().split():
            if token in CALLOUT_TOKENS or token.split("-")[0] in CALLOUT_PREFIXES:
                return True
        return False

    @api.model
    def _detect_callout(self, node, by_class_only=False):
        if self._declares_callout(node):
            # „note trap" е капан, „note key" — извод: тонът е в класа
            return self._tone_of(node) or "info"
        if by_class_only:
            return ""
        return self._marker_level(self._plain_text(node))

    @api.model
    def _marker_level(self, text):
        stripped = (text or "").lstrip()
        for marker, level in CALLOUT_MARKERS.items():
            if stripped.startswith(marker):
                return level
        return ""

    @api.model
    def _detect_kpi(self, node):
        """Показател: класът го обявява И вътре има число с кратък етикет.

        Етикетът поглъща ВСИЧКИ останали текстове в контейнера — иначе третият
        span си отива тихо (намерено при roi-repos: 145 изгубени думи).
        """
        blob = node.get("class") or ""
        if not KPI_CLASS_RE.search(blob):
            return self._detect_number_note(node)
        children = [child for child in node if isinstance(child.tag, str)]
        pairs = [(child, self._plain_text(child)) for child in children]
        pairs = [(child, text) for child, text in pairs if text]
        if not pairs:
            pairs = [(node, self._plain_text(node))]
        # Показателят е ОБЯВЕН с клас, затова кратката стойност в <b> е
        # неговото число, дори да е дата („02.08" — последният push) или
        # версия („v2.10.0"). Иначе такива показатели ставаха карета.
        number = ""
        rest = []
        for child, candidate in pairs:
            if not number and (KPI_TEXT_RE.match(candidate) or (
                    child.tag in ("b", "strong") and len(candidate.strip()) <= 12)):
                number = candidate.strip()
            else:
                rest.append(candidate.strip())
        label = " · ".join(rest).strip(" ·")
        if not number or len(label) > KPI_LABEL_MAX:
            # Не е показател — нека обичайното обхождане си го вземе като текст
            return None
        return self._make_block("kpi", html="", text=" ".join(filter(None, [number, label])),
                                meta={"number": number, "label": label,
                                      "tone": self._tone_of(node, allow_key=False)})

    # ------------------------------------------------------------------
    # Помощни
    # ------------------------------------------------------------------
    @api.model
    def _make_block(self, kind, html="", text="", level=0, lang="", anchor="", meta=None):
        return {
            "kind": kind,
            "sequence": 0,
            "level": level,
            "html": (html or "").strip(),
            "text": re.sub(r"\s+", " ", text or "").strip(),
            "lang": lang or "",
            "anchor": anchor or "",
            "meta": meta or {},
        }

    @api.model
    def _plain_text_of_html(self, source):
        """Целият текст на HTML низ, с интервал между възлите.

        Интервалът е важен: text_content() слепва „5" и „Кой" в „5Кой" и всяко
        сравнение после лъже.
        """
        if not (source or "").strip() or lxml_html is None:
            return ""
        tree = lxml_html.fromstring(source)
        for tag in DROP_TAGS:
            for node in tree.xpath("//%s" % tag):
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
        return re.sub(r"\s+", " ", " ".join(tree.itertext())).strip()

    @api.model
    def _plain_text(self, node):
        return re.sub(r"\s+", " ", node.text_content()).strip()

    @api.model
    def _inner_html(self, node, allow_blocks=False):
        """Вътрешният HTML, изчистен до inline тагове без артефактни атрибути.

        При allow_blocks пускаме и блоковите тагове — иначе таблица, вложена в
        <details>, се разтваря и числата ѝ се слепват едно в друго.
        """
        clone = lxml_html.fromstring(etree.tostring(node, encoding="unicode", with_tail=False))
        allowed = set(KEEP_INLINE)
        if allow_blocks:
            allowed |= {"ul", "ol", "li", "p", "br", "code", "pre", "table", "thead",
                        "tbody", "tfoot", "tr", "th", "td", "caption", "h3", "h4",
                        "h5", "h6", "blockquote", "hr", "dl", "dt", "dd"}
        for element in clone.iter():
            if element is clone or not isinstance(element.tag, str):
                continue
            tag = element.tag.lower()
            if tag in DROP_TAGS:
                element.getparent().remove(element)
                continue
            if tag not in allowed:
                if tag not in BLOCK_WRAPPERS:
                    element.drop_tag()
                    continue
                inline_only = not any(isinstance(inner.tag, str) and inner.tag not in KEEP_INLINE
                                      for inner in element.iterdescendants())
                if allow_blocks and inline_only and (element.text_content() or "").strip():
                    # Вътрешен div само с текст е абзац, не продължение на съседа
                    element.tag = tag = "p"
                else:
                    # Без интервал текстът на съседните div-ове се слепваше:
                    # „конфигуриране" + „Формула" дава „конфигуриранеФормула"
                    element.text = " " + (element.text or "")
                    element.tail = " " + (element.tail or "")
                    element.drop_tag()
                    continue
            # Два класа на артефакта носят смисъл и оцеляват като Odoo форма:
            # името на модел/файл става <code>, чипът става s_badge
            chip = ""
            if tag == "span":
                tokens = set((element.get("class") or "").lower().split())
                if tokens & MONO_TOKENS:
                    element.tag = tag = "code"
                elif tokens & CHIP_TOKENS and (element.text_content() or "").strip():
                    chip = self._chip_class(element)
            keep = KEEP_ATTRS.get(tag, ())
            for attr in list(element.attrib):
                if attr not in keep:
                    del element.attrib[attr]
            if chip:
                element.set("class", chip)
                element.set("data-snippet", "s_badge")
                element.set("data-name", "Badge")
        parts = [clone.text or ""]
        for child in clone:
            # ТУК tail-ът се пази нарочно: той е текстът МЕЖДУ inline таговете
            # вътре в блока. Изхвърля се само tail-ът на самия блок (по-горе).
            parts.append(etree.tostring(child, encoding="unicode"))
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    @api.model
    def _covers(self, title, heading):
        """Заглавието на статията често носи и дата: „Отчет — 02.09.2026".

        Тогава h1-ът „Отчет" не съвпада дословно, но пак е същото заглавие и
        пак не бива да стои втори път в тялото.
        """
        norm = lambda value: re.sub(r"[\W_]+", "", (value or "").lower(), flags=re.UNICODE)
        left, right = norm(title), norm(heading)
        if not left or not right or len(right) < 8:
            return False
        return right in left

    @api.model
    def _same_text(self, left, right):
        norm = lambda value: re.sub(r"[\W_]+", "", (value or "").lower(), flags=re.UNICODE)
        return bool(norm(left)) and norm(left) == norm(right)

    @api.model
    def _slugify(self, text):
        slug = re.sub(r"[^\w\s-]", "", (text or "").lower(), flags=re.UNICODE)
        slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
        return slug[:64]

    # ------------------------------------------------------------------
    # Първо подреждане на блоковете
    # ------------------------------------------------------------------
    @api.model
    def _post_process(self, blocks, title, known_title=None):
        """Изхвърля h1-а, който дублира заглавието, и слепва съседни параграфи."""
        result = []
        titles = [value for value in (title, known_title) if value]
        for block in blocks:
            if (block["kind"] == "heading" and block["level"] == 1
                    and any(self._same_text(block["text"], value)
                            or self._covers(value, block["text"])
                            for value in titles)):
                # Заглавието на статията се рендира от блога, не от съдържанието
                continue
            if (result and block["kind"] == "paragraph"
                    and result[-1]["kind"] == "paragraph"
                    and len(result[-1]["html"]) < 600):
                result[-1]["html"] += block["html"]
                result[-1]["text"] = ("%s %s" % (result[-1]["text"], block["text"])).strip()
                continue
            result.append(block)
        while result and result[-1]["kind"] == "separator":
            result.pop()
        return result

    # ------------------------------------------------------------------
    # Минимален Markdown -> HTML (подмножеството, което Claude пише)
    # ------------------------------------------------------------------
    @api.model
    def _markdown_to_html(self, text):
        out = []
        lines = (text or "").replace("\r\n", "\n").split("\n")
        index = 0
        while index < len(lines):
            line = lines[index]
            fence = re.match(r"^\s*```\s*([\w+#.-]*)\s*$", line)
            if fence:
                lang = fence.group(1)
                index += 1
                body = []
                while index < len(lines) and not re.match(r"^\s*```\s*$", lines[index]):
                    body.append(lines[index])
                    index += 1
                index += 1
                cls = ' class="language-%s"' % lang if lang else ""
                out.append("<pre><code%s>%s</code></pre>" % (
                    cls, self._md_escape("\n".join(body))))
                continue
            heading = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading:
                level = len(heading.group(1))
                out.append("<h%d>%s</h%d>" % (level, self._md_inline(heading.group(2)), level))
                index += 1
                continue
            if re.match(r"^\s*([-*_])\s*\1\s*\1[\s\1]*$", line):
                out.append("<hr/>")
                index += 1
                continue
            if re.match(r"^\s*\|.*\|\s*$", line):
                rows, index = self._md_table(lines, index)
                out.append(rows)
                continue
            if re.match(r"^\s*[-*+]\s+", line) or re.match(r"^\s*\d+[.)]\s+", line):
                items, index, ordered = self._md_list(lines, index)
                tag = "ol" if ordered else "ul"
                out.append("<%s>%s</%s>" % (tag, "".join(items), tag))
                continue
            if re.match(r"^\s*>\s?", line):
                quote = []
                while index < len(lines) and re.match(r"^\s*>\s?", lines[index]):
                    quote.append(re.sub(r"^\s*>\s?", "", lines[index]))
                    index += 1
                out.append("<blockquote><p>%s</p></blockquote>"
                           % self._md_inline(" ".join(quote)))
                continue
            if line.strip():
                para = []
                while index < len(lines) and lines[index].strip() \
                        and not re.match(r"^\s*(#{1,6}\s|```|\||[-*+]\s|\d+[.)]\s|>)", lines[index]):
                    para.append(lines[index].strip())
                    index += 1
                out.append("<p>%s</p>" % self._md_inline(" ".join(para)))
                continue
            index += 1
        return "<html><body>%s</body></html>" % "".join(out)

    @api.model
    def _md_list(self, lines, index):
        items = []
        ordered = bool(re.match(r"^\s*\d+[.)]\s+", lines[index]))
        pattern = r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$"
        while index < len(lines):
            match = re.match(pattern, lines[index])
            if not match:
                break
            items.append("<li>%s</li>" % self._md_inline(match.group(1)))
            index += 1
        return items, index, ordered

    @api.model
    def _md_table(self, lines, index):
        rows = []
        header_done = False
        while index < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[index]):
            raw = lines[index].strip().strip("|")
            if re.fullmatch(r"[\s:|-]+", raw):
                header_done = True
                index += 1
                continue
            tag = "th" if not header_done and not rows else "td"
            cells = ["<%s>%s</%s>" % (tag, self._md_inline(c.strip()), tag)
                     for c in raw.split("|")]
            rows.append("<tr>%s</tr>" % "".join(cells))
            index += 1
        return "<table>%s</table>" % "".join(rows), index

    @api.model
    def _md_escape(self, text):
        return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @api.model
    def _md_inline(self, text):
        text = self._md_escape(text or "")
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
        return text
