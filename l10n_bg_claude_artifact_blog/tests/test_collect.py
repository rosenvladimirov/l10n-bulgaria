# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Входът от Claude сесия и изходът към блога.

Правилото, което не се договаря: към сайта не тръгва нищо без човек.
"""

import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from .fixtures.sample_artifact import ARTIFACT_HTML, ARTIFACT_MARKDOWN


class TestArtifactCollect(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.artifacts = cls.env["claude.artifact"]
        cls.blog = cls.env["blog.blog"].create({"name": "Test Blog"})

    def test_collect_parses_and_reports(self):
        result = self.artifacts.collect({
            "title": "Разчетът на склада",
            "content": ARTIFACT_HTML,
            "session": "sess-1",
        })
        self.assertFalse(result["reused"])
        self.assertEqual(result["state"], "parsed")
        self.assertGreater(result["blocks"], 10)
        self.assertIn("kpi_group", result["kinds"])

    def test_collect_is_idempotent_on_the_same_content(self):
        first = self.artifacts.collect({"title": "A", "content": ARTIFACT_HTML})
        second = self.artifacts.collect({"title": "A", "content": ARTIFACT_HTML})
        self.assertTrue(second["reused"])
        self.assertEqual(first["id"], second["id"])

    def test_collect_can_build_immediately(self):
        result = self.artifacts.collect({
            "title": "B", "content": ARTIFACT_MARKDOWN,
            "format": "markdown", "build": True,
        })
        artifact = self.artifacts.browse(result["id"])
        self.assertEqual(artifact.state, "built")
        self.assertIn("s_text_block", artifact.built_content)

    def test_collect_refuses_empty_and_unknown_format(self):
        with self.assertRaises(UserError):
            self.artifacts.collect({"title": "C", "content": "  "})
        with self.assertRaises(UserError):
            self.artifacts.collect({"title": "C", "content": "x", "format": "pdf"})

    def test_session_report_lists_what_was_collected(self):
        self.artifacts.collect({
            "title": "D", "content": ARTIFACT_HTML.replace("склада", "цеха"),
            "session": "sess-report",
        })
        report = self.artifacts.report_for_session("sess-report")
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]["name"], "D")

    def test_script_rendered_artifact_is_refused_with_a_diagnosis(self):
        """Артефакт, който се рисува от скрипт: <body> носи празен <div>, а
        целият текст е вътре в <script>. Парсерът изхвърля скриптовете и
        остава с нищо. Такъв запис не бива да ляга тихо с нула блока —
        намерено при качването на specs: два артефакта по 2,4 MB."""
        payload = (
            "<html><head><title>Клиентски рендер</title></head><body>"
            "<div id=\"root\"></div>"
            "<script>var DATA=[%s];</script>"
            "</body></html>" % ",".join('"дума%d"' % i for i in range(400))
        )
        with self.assertRaises(UserError) as caught:
            self.artifacts.collect({"title": "Клиентски рендер", "content": payload})
        self.assertIn("scripts", str(caught.exception))

    def test_coverage_separates_dropped_from_lost(self):
        """h1 става заглавие, standfirst — подзаглавие, а надзаглавието се
        изхвърля нарочно (блогът си показва датата). Ако отчетът брои и трите
        за липса, гърми при всеки артефакт — а гард, който гърми винаги, е шум."""
        result = self.artifacts.collect({
            "content": ARTIFACT_HTML.replace("склада", "килера"), "build": True,
        })
        artifact = self.artifacts.browse(result["id"])
        report = artifact._coverage_report()
        self.assertGreaterEqual(report["coverage"], 99.0, report)
        missing = (report["sample"] or "").lower()
        self.assertNotIn("работен", missing, "надзаглавието не е загуба")
        self.assertNotIn("разчетът", missing, "заглавието не е загуба")
        self.assertGreater(report["dropped_words"], 0, "надзаглавието се отчита отделно")

    # ------------------------------------------------------------------
    def test_blog_post_is_created_as_a_draft(self):
        result = self.artifacts.collect({
            "title": "E", "content": ARTIFACT_HTML.replace("склада", "рафта"),
            "blog_id": self.blog.id, "build": True,
        })
        artifact = self.artifacts.browse(result["id"])
        artifact.action_publish_draft()
        post = artifact.blog_post_id
        self.assertTrue(post)
        self.assertFalse(post.website_published, "нищо не тръгва към сайта само")
        self.assertEqual(post.blog_id, self.blog)
        self.assertIn("s_title", post.content)

    def test_post_carries_its_seo_fields_and_a_readable_teaser(self):
        """Без мета полетата страницата тръгва с „Page title not set", а
        автоматичният откъс взема ОГЛАВЛЕНИЕТО — то стои първо в съдържанието
        и дава „01Какво се иска 02Заварено състояние"."""
        result = self.artifacts.collect({
            "title": "Разчетът на склада",
            "content": ARTIFACT_HTML.replace("склада", "тавана2"),
            "blog_id": self.blog.id, "build": True,
        })
        artifact = self.artifacts.browse(result["id"])
        artifact.action_publish_draft()
        post = artifact.blog_post_id
        self.assertEqual(post.website_meta_title, "Разчетът на склада")
        self.assertTrue(post.website_meta_description)
        self.assertIn("Кратък водещ абзац", post.website_meta_description)
        self.assertTrue(post.teaser_manual)
        self.assertNotIn("01", post.teaser_manual[:4], "откъсът не е оглавлението")
        self.assertIn("Какво беше измерено", post.website_meta_keywords)

    def test_publishing_twice_updates_the_same_post(self):
        result = self.artifacts.collect({
            "title": "F", "content": ARTIFACT_HTML.replace("склада", "пода"),
            "blog_id": self.blog.id, "build": True,
        })
        artifact = self.artifacts.browse(result["id"])
        artifact.action_publish_draft()
        post_id = artifact.blog_post_id.id
        artifact.action_publish_draft()
        self.assertEqual(artifact.blog_post_id.id, post_id)
        self.assertEqual(
            self.env["blog.post"].search_count([("name", "=", "F")]), 1)

    def test_publishing_without_a_blog_is_refused(self):
        result = self.artifacts.collect({
            "title": "G", "content": ARTIFACT_HTML.replace("склада", "тавана"),
        })
        artifact = self.artifacts.browse(result["id"])
        with self.assertRaises(UserError):
            artifact.action_publish_draft()

    def test_subtitle_is_taken_from_the_standfirst(self):
        result = self.artifacts.collect({
            "title": "H", "content": ARTIFACT_HTML.replace("склада", "двора"),
        })
        artifact = self.artifacts.browse(result["id"])
        self.assertIn("Кратък водещ абзац", artifact.subtitle or "")

    # ------------------------------------------------------------------
    def test_import_wizard_reads_an_uploaded_file(self):
        wizard = self.env["claude.artifact.import.wizard"].create({
            "upload_file": base64.b64encode(
                ARTIFACT_HTML.replace("склада", "мазето").encode("utf-8")),
            "upload_filename": "artifact.html",
            "blog_id": self.blog.id,
        })
        action = wizard.action_import()
        artifact = self.artifacts.browse(action["res_id"])
        self.assertEqual(artifact.state, "built")
        self.assertEqual(artifact.blog_id, self.blog)

    def test_import_wizard_detects_markdown_by_extension(self):
        wizard = self.env["claude.artifact.import.wizard"].new({
            "upload_filename": "notes.md",
        })
        wizard._onchange_upload_filename()
        self.assertEqual(wizard.source_format, "markdown")

    def test_import_wizard_refuses_an_empty_form(self):
        wizard = self.env["claude.artifact.import.wizard"].create({})
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_publish_wizard_creates_drafts_for_the_selection(self):
        ids = []
        for suffix in ("щанда", "хангара"):
            result = self.artifacts.collect({
                "title": suffix, "content": ARTIFACT_HTML.replace("склада", suffix),
            })
            ids.append(result["id"])
        wizard = self.env["claude.artifact.publish.wizard"].create({
            "artifact_ids": [(6, 0, ids)],
            "blog_id": self.blog.id,
        })
        wizard.action_publish()
        posts = self.artifacts.browse(ids).mapped("blog_post_id")
        self.assertEqual(len(posts), 2)
        self.assertFalse(any(post.website_published for post in posts))
