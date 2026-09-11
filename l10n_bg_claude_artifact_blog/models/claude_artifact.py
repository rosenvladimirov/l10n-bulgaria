# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Колекцията от артефакти и сглобяването на блог статия от Odoo снипети.

Пътят е на четири стъпки, всяка със свой видим резултат:
  събран -> парснат (блокове) -> сглобен (content) -> публикуван (blog.post)
Публикуването ВИНАГИ прави чернова. Нищо не тръгва към сайта без човек.
"""

import hashlib
import json
import logging
import re

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Икона на предупреждението по ниво — Odoo рендира FontAwesome в s_alert
ALERT_ICONS = {
    "info": "info-circle",
    "success": "check-circle",
    "warning": "exclamation-triangle",
    "danger": "exclamation-circle",
}

# Над този брой заглавия от второ ниво статията получава оглавление
TOC_THRESHOLD = 4


class ClaudeArtifact(models.Model):
    _name = "claude.artifact"
    _description = "Claude Artifact"
    _inherit = ["mail.thread"]
    _order = "captured_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    subtitle = fields.Char(help="Filled from the artifact standfirst when present.")
    state = fields.Selection(
        [
            ("collected", "Collected"),
            ("parsed", "Parsed"),
            ("built", "Built"),
            ("published", "Published"),
        ],
        default="collected", required=True, tracking=True, index=True,
    )
    source_format = fields.Selection(
        [("html", "HTML"), ("markdown", "Markdown")], default="html", required=True,
    )
    source_url = fields.Char(
        "Artifact URL",
        help="Where the artifact lives on claude.ai. Kept for the record only — "
             "artifact links are not a reliable identifier over time.",
    )
    artifact_uid = fields.Char(
        "Artifact ID", index=True,
        help="The artifact identifier as reported by the Claude session.",
    )
    session_ref = fields.Char(
        "Session", help="Free reference to the conversation that produced it.",
    )
    raw_source = fields.Text(required=True)
    checksum = fields.Char(
        index=True, readonly=True, copy=False,
        help="SHA-256 of the normalised source, used to recognise a re-send.",
    )
    captured_date = fields.Datetime(default=fields.Datetime.now, required=True)
    block_ids = fields.One2many("claude.artifact.block", "artifact_id")
    block_count = fields.Integer(compute="_compute_block_count")

    # ---- целта на публикуването -------------------------------------
    blog_id = fields.Many2one("blog.blog", "Target Blog")
    author_id = fields.Many2one(
        "res.partner", "Author", default=lambda self: self.env.user.partner_id,
    )
    tag_ids = fields.Many2many("blog.tag", string="Tags")
    blog_post_id = fields.Many2one("blog.post", readonly=True, copy=False)
    use_table_of_content = fields.Selection(
        [("auto", "Automatic"), ("always", "Always"), ("never", "Never")],
        default="auto", required=True,
        help="Long artifacts read better with the sticky navigation of the "
             "Table of Content snippet.",
    )
    built_content = fields.Html(
        "Built Content", sanitize=False, readonly=True, copy=False,
        help="What will be written into the blog post — snippets, not a dump.",
    )
    note = fields.Text()

    _checksum_uniq = models.Constraint(
        "unique (checksum)",
        "This artifact has already been collected.",
    )

    # ------------------------------------------------------------------
    # Изчислени
    # ------------------------------------------------------------------
    @api.depends("block_ids")
    def _compute_block_count(self):
        data = self.env["claude.artifact.block"]._read_group(
            [("artifact_id", "in", self.ids)], ["artifact_id"], ["__count"],
        )
        counts = {artifact.id: count for artifact, count in data}
        for artifact in self:
            artifact.block_count = counts.get(artifact.id, 0)

    # ------------------------------------------------------------------
    # Събиране
    # ------------------------------------------------------------------
    @api.model
    def _normalise(self, source):
        return re.sub(r"\s+", " ", source or "").strip()

    @api.model
    def _checksum_of(self, source):
        return hashlib.sha256(self._normalise(source).encode("utf-8")).hexdigest()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("raw_source") and not vals.get("checksum"):
                vals["checksum"] = self._checksum_of(vals["raw_source"])
        return super().create(vals_list)

    def write(self, vals):
        if "raw_source" in vals:
            vals["checksum"] = self._checksum_of(vals["raw_source"])
        return super().write(vals)

    @api.model
    def collect(self, payload):
        """Входът за Claude сесия през RPC/MCP.

        Приема dict и връща dict — нарочно, за да е викаем от външен агент без
        да знае имената на полетата на blog.post. Съществуващият артефакт със
        същото съдържание се връща, вместо да се дублира.
        """
        if not isinstance(payload, dict):
            raise UserError(_("The artifact payload must be a dictionary."))
        source = payload.get("content") or payload.get("html") or ""
        if not (source or "").strip():
            raise UserError(_("The artifact payload carries no content."))
        checksum = self._checksum_of(source)
        existing = self.search([("checksum", "=", checksum)], limit=1)
        if existing:
            return existing._collect_result(reused=True)

        source_format = payload.get("format") or "html"
        if source_format not in ("html", "markdown"):
            raise UserError(
                _("Unknown artifact format %s; expected html or markdown.",
                  source_format)
            )
        vals = {
            "name": payload.get("title") or _("Untitled artifact"),
            "raw_source": source,
            "source_format": source_format,
            "source_url": payload.get("url") or "",
            "artifact_uid": payload.get("artifact_id") or "",
            "session_ref": payload.get("session") or "",
            "note": payload.get("note") or "",
        }
        if payload.get("blog_id"):
            vals["blog_id"] = payload["blog_id"]
        artifact = self.create(vals)
        artifact.action_parse()
        if payload.get("title"):
            # Заглавието от сесията бие това, което парсерът е намерил
            artifact.name = payload["title"]
        if payload.get("build"):
            artifact.action_build()
        return artifact._collect_result(reused=False)

    def _collect_result(self, reused=False):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "reused": reused,
            "blocks": self.block_count,
            "kinds": self._block_kind_summary(),
            "blog_post_id": self.blog_post_id.id or False,
            "url": self.blog_post_id.website_url if self.blog_post_id else "",
        }

    def _block_kind_summary(self):
        summary = {}
        for block in self.block_ids:
            summary[block.kind] = summary.get(block.kind, 0) + 1
        return summary

    # ------------------------------------------------------------------
    # Парсване
    # ------------------------------------------------------------------
    def action_parse(self):
        parser = self.env["claude.artifact.parser"]
        blocks_model = self.env["claude.artifact.block"]
        for artifact in self:
            artifact.block_ids.unlink()
            known = artifact.name if artifact.name != _("Untitled artifact") else None
            title, blocks = parser.parse(
                artifact.raw_source, artifact.source_format, known_title=known)
            vals = []
            subtitle = artifact.subtitle
            for block in blocks:
                if block["kind"] == "standfirst" and not subtitle:
                    subtitle = block["text"][:255]
                vals.append(dict(blocks_model._vals_from_parsed(block),
                                 artifact_id=artifact.id))
            if not vals:
                raise UserError(artifact._nothing_to_parse_message())
            blocks_model.create(vals)
            artifact.write({
                "name": artifact.name if artifact.name != _("Untitled artifact")
                        else (title or artifact.name),
                "subtitle": subtitle,
                "state": "parsed",
                "built_content": False,
            })
            artifact.message_post(
                body=_("Parsed into %(count)s blocks: %(kinds)s",
                       count=len(blocks),
                       kinds=", ".join("%s×%s" % (kind, count) for kind, count
                                       in sorted(artifact._block_kind_summary().items())))
            )
        return True

    # ------------------------------------------------------------------
    # Сглобяване на съдържанието
    # ------------------------------------------------------------------
    def action_build(self):
        for artifact in self:
            if not artifact.block_ids:
                artifact.action_parse()
            artifact.built_content = artifact._render_content()
            artifact.state = "built"
        return True

    def _render_content(self):
        """Сглобява content-а: снипет по снипет, в реда на блоковете."""
        self.ensure_one()
        rules = self.env["claude.snippet.rule"]
        sections = []          # готови парчета HTML
        toc_entries = []       # (anchor, label) за оглавлението
        buffer = []            # непълни (нестандартни) блокове, чакащи текстова секция
        heading_index = 0

        def flush():
            if not buffer:
                return
            body = Markup("").join(buffer)
            sections.append(self._render_template(
                "l10n_bg_claude_artifact_blog.snippet_text_block", {"body": body}))
            buffer.clear()

        for block in self.block_ids.sorted(lambda b: (b.sequence, b.id)):
            if block.excluded or block.kind == "kicker":
                continue
            rule = block.rule_id or rules._rule_for(block)
            if not rule:
                _logger.warning("No snippet rule for block %s (%s); kept as text",
                                block.id, block.kind)
                buffer.append(Markup(block.body_html or ""))
                continue
            if rule.starts_section:
                flush()
                heading_index += 1
                anchor = "table_of_content_heading_1_%d" % heading_index
                toc_entries.append({"anchor": anchor, "label": block.text})
                sections.append(self._render_template(rule.template_key, {
                    "anchor": anchor,
                    "markup": Markup(self._heading_inner(block)),
                }))
                continue
            if not rule.standalone:
                buffer.append(Markup(self._inline_markup(block)))
                continue
            flush()
            sections.append(self._render_template(
                rule.template_key, self._template_values(block)))
        flush()

        body = Markup("").join(sections)
        if self._wants_toc(toc_entries):
            body = self._render_template(
                "l10n_bg_claude_artifact_blog.snippet_table_of_content",
                {"entries": toc_entries, "body": body},
            )
        return body

    def _wants_toc(self, toc_entries):
        self.ensure_one()
        if self.use_table_of_content == "never":
            return False
        if self.use_table_of_content == "always":
            return bool(toc_entries)
        return len(toc_entries) >= TOC_THRESHOLD

    def _render_template(self, template_key, values):
        return self.env["ir.qweb"]._render(template_key, values, minimal_qcontext=True)

    # ------------------------------------------------------------------
    # Стойностите за всеки снипет
    # ------------------------------------------------------------------
    def _heading_inner(self, block):
        markup = block.body_html or ""
        match = re.match(r"^\s*<h[1-6][^>]*>(.*)</h[1-6]>\s*$", markup, re.DOTALL)
        return match.group(1) if match else (block.text or "")

    def _inline_markup(self, block):
        """Блок, който живее вътре в текстова секция."""
        if block.kind == "heading":
            level = min(max(block.level or 3, 3), 6)
            classes = {3: "h4-fs", 4: "h5-fs", 5: "h6-fs", 6: "h6-fs"}[level]
            return '<h%d class="%s">%s</h%d>' % (
                level, classes, self._heading_inner(block), level)
        if block.kind == "caption":
            return '<p class="o_small text-muted">%s</p>' % (block.text or "")
        return self._wrap_tables(block.body_html or "")

    @api.model
    def _wrap_tables(self, markup):
        """Обвива всяка таблица в скролер и ѝ слага класовете на Odoo.

        Таблицата, вложена в <details> или в предупреждение, стигаше сурова до
        статията: широка таблица без .table-responsive вади цялата страница
        настрани на телефон.
        """
        if not markup or "<table" not in markup:
            return markup or ""
        from lxml import etree, html as lxml_html
        holder = lxml_html.fragment_fromstring(markup, create_parent="div")
        for table in holder.xpath(".//table"):
            classes = set((table.get("class") or "").split())
            classes.update(["table", "table-sm", "table-hover", "align-middle"])
            table.set("class", " ".join(sorted(classes)))
            parent = table.getparent()
            if "table-responsive" in (parent.get("class") or ""):
                continue
            wrapper = etree.Element("div")
            wrapper.set("class", "table-responsive")
            parent.replace(table, wrapper)
            wrapper.append(table)
            wrapper.tail = table.tail
            table.tail = None
        parts = [holder.text or ""]
        parts.extend(etree.tostring(child, encoding="unicode") for child in holder)
        return "".join(parts)

    def _template_values(self, block):
        meta = block.meta
        kind = block.kind
        if kind == "callout":
            level = meta.get("level") or "info"
            return {
                "level": level,
                "icon": ALERT_ICONS.get(level, "info-circle"),
                "body": Markup(self._wrap_tables(
                    block.body_html or "<p>%s</p>" % (block.text or ""))),
            }
        if kind == "quote":
            return {"markup": Markup(block.body_html or ""), "cite": meta.get("cite") or ""}
        if kind == "kpi":
            return {"number": meta.get("number") or "", "label": meta.get("label") or ""}
        if kind in ("kpi_group", "definitions"):
            pairs = meta.get("pairs") or []
            return {
                "pairs": pairs,
                "column_width": 4 if len(pairs) % 3 == 0 or len(pairs) > 4 else 6,
            }
        if kind == "code":
            return {"code": block.text or "", "lang": block.lang or ""}
        if kind == "table":
            return {
                "rows": Markup(block.body_html or ""),
                "caption": meta.get("caption") or "",
            }
        if kind == "svg":
            return {
                "svg": Markup(block.body_html or ""),
                "caption": meta.get("caption") or "",
            }
        if kind == "image":
            return {
                "src": meta.get("src") or "",
                "alt": meta.get("alt") or "",
                "caption": meta.get("caption") or "",
            }
        if kind == "accordion":
            token = "artifact%d_%d" % (self.id, block.id)
            return {
                "summary": meta.get("summary") or block.text or "",
                "body": Markup(self._wrap_tables(block.body_html or "")),
                "group_id": "acc_%s" % token,
                "button_id": "accbtn_%s" % token,
                "panel_id": "accpanel_%s" % token,
            }
        if kind == "standfirst":
            return {"markup": Markup(self._heading_inner(block) or block.text or "")}
        if kind == "separator":
            return {}
        return {"body": Markup(block.body_html or "")}

    # ------------------------------------------------------------------
    # Публикуване
    # ------------------------------------------------------------------
    def action_publish_draft(self):
        """Създава или обновява блог поста — ВИНАГИ като чернова."""
        for artifact in self:
            if not artifact.blog_id:
                raise UserError(
                    _("Pick a target blog for %s before publishing.", artifact.name)
                )
            if not artifact.built_content:
                artifact.action_build()
            summary = artifact._summary_text()
            vals = {
                "name": artifact.name,
                "subtitle": artifact.subtitle or "",
                "blog_id": artifact.blog_id.id,
                "author_id": artifact.author_id.id or self.env.user.partner_id.id,
                "content": artifact.built_content,
                "tag_ids": [(6, 0, artifact.tag_ids.ids)],
                # Без тези полета страницата тръгва с „Page title not set",
                # а автоматичният откъс взема ОГЛАВЛЕНИЕТО — то стои първо в
                # съдържанието и дава „01Какво се иска 02Заварено състояние".
                "teaser_manual": summary,
                "website_meta_title": artifact.name,
                "website_meta_description": summary,
                "website_meta_keywords": artifact._meta_keywords(),
            }
            if artifact.blog_post_id:
                artifact.blog_post_id.write(vals)
                post = artifact.blog_post_id
            else:
                vals["website_published"] = False
                post = self.env["blog.post"].create(vals)
                artifact.blog_post_id = post
            artifact.state = "published"
            artifact.message_post(
                body=_("Blog post draft %(id)s updated from %(count)s blocks.",
                       id=post.id, count=artifact.block_count)
            )
        return True

    def _summary_text(self, limit=160):
        """Резюмето за откъса и за мета описанието.

        Взема водещия абзац, а ако няма — първия истински текстов блок.
        Оглавлението и надзаглавието се прескачат: те не описват статията.
        """
        self.ensure_one()
        if self.subtitle:
            return self.subtitle[:limit]
        for block in self.block_ids.sorted(lambda b: (b.sequence, b.id)):
            if block.excluded or block.kind not in ("standfirst", "paragraph"):
                continue
            text = (block.text or "").strip()
            if len(text) > 40:
                return text[:limit]
        return (self.name or "")[:limit]

    def _meta_keywords(self, count=8):
        """Ключовите думи са заглавията на секциите — те са реалните теми.

        По-добре празно, отколкото измислени: ако артефактът няма секции,
        полето остава празно.
        """
        self.ensure_one()
        headings = self.block_ids.filtered(
            lambda block: block.kind == "heading" and block.level == 2
            and not block.excluded)
        words = [heading.text.strip() for heading in headings if heading.text]
        return ", ".join(words[:count])

    def action_open_post(self):
        self.ensure_one()
        if not self.blog_post_id:
            raise UserError(_("No blog post has been created for this artifact yet."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "blog.post",
            "res_id": self.blog_post_id.id,
            "view_mode": "form",
        }

    def action_view_blocks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Blocks of %s", self.name),
            "res_model": "claude.artifact.block",
            "view_mode": "list,form",
            "domain": [("artifact_id", "=", self.id)],
            "context": {"default_artifact_id": self.id},
        }

    # ------------------------------------------------------------------
    # Самопроверка: носи ли статията текста на артефакта
    # ------------------------------------------------------------------
    def action_check_coverage(self):
        """Сравнява думите на източника с думите на сглобения content.

        Гоненето на снипети може тихо да изяде цяла таблица. Затова числото се
        мери върху РЕЗУЛТАТА, не върху блоковете — и се записва в чатъра.
        """
        for artifact in self:
            if not artifact.built_content:
                artifact.action_build()
            report = artifact._coverage_report()
            artifact.message_post(body=Markup(
                _("<p>Coverage: <b>%(pct).1f%%</b> — source %(src)s words, "
                  "article %(got)s words, missing %(lost)s, "
                  "dropped on purpose %(dropped)s.</p>%(sample)s")
            ) % {
                "pct": report["coverage"],
                "src": report["source_words"],
                "got": report["built_words"],
                "lost": report["missing_words"],
                "dropped": report["dropped_words"],
                "sample": Markup("<p>%s</p>") % report["sample"]
                          if report["sample"] else Markup(""),
            })
        return True

    def _nothing_to_parse_message(self):
        """Диагнозата, когато артефактът не дава нито един блок.

        Най-честата причина е артефакт, който се рисува от скрипт: <body>
        носи празен <div> и няколко <script>, а целият текст живее вътре в
        скрипта. Парсерът изхвърля скриптовете нарочно — те не бива да влизат
        в блога — и остава с нищо. Такъв артефакт иска изпълнен JavaScript,
        а не разбор на разметка.
        """
        self.ensure_one()
        parser = self.env["claude.artifact.parser"]
        visible = len(parser._plain_text_of_html(self.raw_source).split())
        raw_words = len((self.raw_source or "").split())
        if raw_words and visible * 20 < raw_words:
            return _(
                "The artifact %(name)s carries no readable markup: its text "
                "lives inside its scripts, not in the document. Such an "
                "artifact has to be rendered by a browser first — export it "
                "as plain HTML or Markdown and collect that instead.",
                name=self.name,
            )
        return _(
            "The artifact %(name)s produced no blocks. Check that it really "
            "is an HTML or Markdown document.",
            name=self.name,
        )

    def _coverage_report(self):
        self.ensure_one()
        parser = self.env["claude.artifact.parser"]
        source_words = self._word_counter(
            parser._plain_text_of_html(self.raw_source)
            if self.source_format == "html" else self.raw_source
        )
        # Изхвърленото нарочно не е изгубено. Надзаглавието („технически
        # разчет · 11.09.2026") е метаред, който блогът и без това показва
        # със собствената си дата; изключените блокове са избор на човека.
        # Без това разграничение числото гърми при всеки артефакт с kicker.
        dropped = self.block_ids.filtered(
            lambda block: block.excluded or block.kind == "kicker")
        for block in dropped:
            source_words -= self._word_counter(block.text)
        # Заглавието и подзаглавието НЕ се губят: те стават name и subtitle
        # на статията. Без тях отчетът показва липса при всеки артефакт с
        # надзаглавие — а гард, който гърми винаги, е шум.
        built_words = self._word_counter(" ".join([
            parser._plain_text_of_html(self.built_content or ""),
            self.name or "",
            self.subtitle or "",
        ]))
        missing = source_words - built_words
        total = sum(source_words.values())
        dropped_words = sum(self._word_counter(block.text).total()
                            for block in dropped)
        return {
            "source_words": total,
            "dropped_words": dropped_words,
            "built_words": sum(built_words.values()),
            "missing_words": sum(missing.values()),
            "coverage": 100.0 * sum(built_words.values()) / (total or 1),
            "sample": ", ".join("%s×%s" % (word, count)
                                for word, count in missing.most_common(10)),
        }

    @api.model
    def _word_counter(self, text):
        from collections import Counter
        return Counter(re.findall(r"[\wЀ-ӿ%]+", text or "", re.UNICODE))

    # ------------------------------------------------------------------
    # Отчет за сесията, която е събрала артефакта
    # ------------------------------------------------------------------
    @api.model
    def report_for_session(self, session_ref):
        artifacts = self.search([("session_ref", "=", session_ref)])
        return json.loads(json.dumps([
            artifact._collect_result() for artifact in artifacts
        ]))
