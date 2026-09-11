# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Детерминистичен парсер: самостоятелен Claude артефакт -> плосък списък блокове.

Тук НЯМА нито ред LLM. Артефактът е HTML и структурата му е носителят на
смисъла: h2 значи секция, pre значи код, table значи таблица. Мапването към
Odoo снипети е ОТДЕЛНА стъпка (claude.snippet.rule) — парсерът само казва
какво е видял, не как ще изглежда.
"""

import logging
import re

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

# Клас/роля, която прави блока предупреждение независимо от текста
CALLOUT_CLASS_RE = re.compile(
    r"(?i)\b(alert|callout|warning|danger|notice|admonition|caution|tip|note|info-box)\b"
)

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
            if tag in FIGURE_TAGS:
                self._walk_figure(child, blocks)
                tail = (child.tail or "").strip()
                if tail:
                    blocks.append(self._make_block("paragraph", html="<p>%s</p>" % tail,
                                                   text=tail))
                continue
            kind = BLOCK_HANDLERS.get(tag)
            if kind:
                block = self._build(kind, child, tag)
                if block:
                    blocks.append(block)
                elif [grand for grand in child if isinstance(grand.tag, str)]:
                    # Билдърът не разпозна нищо, но вътре ИМА съдържание —
                    # слизаме, вместо да го изядем тихо (намерено: <details>
                    # с таблица, скрит вътре в <figure>)
                    self._walk(child, blocks)
            elif tag in CONTAINER_TAGS:
                callout = self._detect_callout(child)
                if callout and self._plain_text(child):
                    blocks.append(self._make_block(
                        "callout",
                        html=self._inner_html(child),
                        text=self._plain_text(child),
                        meta={"level": callout},
                    ))
                    continue
                kpi = self._detect_kpi(child)
                if kpi:
                    blocks.append(kpi)
                    continue
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
    # Блокове по вид
    # ------------------------------------------------------------------
    @api.model
    def _build_heading(self, node, tag):
        self._drop_heading_number(node)
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
        rows = []
        for row in node.xpath(".//tr"):
            cells = []
            for cell in row.xpath("./th|./td"):
                cell_tag = "th" if cell.tag == "th" else "td"
                cells.append("<%s>%s</%s>" % (cell_tag, self._inner_html(cell), cell_tag))
            if cells:
                rows.append("<tr>%s</tr>" % "".join(cells))
        if not rows:
            return None
        caption = node.xpath("./caption//text()")
        return self._make_block(
            "table",
            html="".join(rows),
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
    def _detect_callout(self, node):
        blob = " ".join(filter(None, [node.get("class") or "", node.get("role") or "",
                                      node.get("data-name") or ""]))
        if node.get("role") == "alert" or CALLOUT_CLASS_RE.search(blob):
            for level in ("danger", "warning", "success", "info"):
                if level in blob.lower():
                    return level
            return "info"
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
            return None
        children = [child for child in node if isinstance(child.tag, str)]
        texts = [self._plain_text(child) for child in children]
        texts = [text for text in texts if text]
        if not texts:
            texts = [self._plain_text(node)]
        number = ""
        rest = []
        for candidate in texts:
            if not number and KPI_TEXT_RE.match(candidate):
                number = candidate.strip()
            else:
                rest.append(candidate.strip())
        label = " · ".join(rest).strip(" ·")
        if not number or len(label) > KPI_LABEL_MAX:
            # Не е показател — нека обичайното обхождане си го вземе като текст
            return None
        return self._make_block("kpi", html="", text=" ".join(filter(None, [number, label])),
                                meta={"number": number, "label": label})

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
                element.drop_tag()
                continue
            keep = KEEP_ATTRS.get(tag, ())
            for attr in list(element.attrib):
                if attr not in keep:
                    del element.attrib[attr]
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
