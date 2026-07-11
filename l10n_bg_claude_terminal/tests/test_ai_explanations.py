# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models
from odoo.tests.common import TransactionCase, tagged

from ..models.ir_model import _extract_lang


@tagged("post_install", "-at_install")
class TestExtractLang(TransactionCase):
    """Unit tests for the language-filtering parser."""

    def test_no_text(self):
        self.assertIsNone(_extract_lang("", "bg_BG"))
        self.assertIsNone(_extract_lang(None, "en_US"))

    def test_unmarked_defaults_to_en_us(self):
        text = "Plain English description without markers."
        self.assertEqual(_extract_lang(text, "en_US"), text)
        self.assertIsNone(_extract_lang(text, "bg_BG"))
        self.assertIsNone(_extract_lang(text, "de_DE"))

    def test_single_marker_block(self):
        text = "[bg_BG]Българска поръчка.[/bg_BG]"
        self.assertEqual(_extract_lang(text, "bg_BG"), "Българска поръчка.")
        self.assertIsNone(_extract_lang(text, "en_US"))

    def test_multiple_marker_blocks(self):
        text = (
            "[bg_BG]Българска поръчка.[/bg_BG]\n"
            "[en_US]Sale order.[/en_US]"
        )
        self.assertEqual(_extract_lang(text, "bg_BG"), "Българска поръчка.")
        self.assertEqual(_extract_lang(text, "en_US"), "Sale order.")
        self.assertIsNone(_extract_lang(text, "de_DE"))

    def test_mixed_unmarked_and_marked(self):
        """When markers exist, unmarked prose is discarded."""
        text = "Stray unmarked text. [bg_BG]Само българското.[/bg_BG]"
        self.assertEqual(_extract_lang(text, "bg_BG"), "Само българското.")
        self.assertIsNone(_extract_lang(text, "en_US"))

    def test_multiline_marker_block(self):
        text = (
            "[bg_BG]\n"
            "Ред едно.\n"
            "Ред две.\n"
            "[/bg_BG]"
        )
        self.assertEqual(
            _extract_lang(text, "bg_BG"),
            "Ред едно.\nРед две.",
        )

    def test_duplicate_lang_blocks_concatenated(self):
        text = "[bg_BG]Първи.[/bg_BG][bg_BG]Втори.[/bg_BG]"
        self.assertEqual(_extract_lang(text, "bg_BG"), "Първи.\n\nВтори.")


@tagged("post_install", "-at_install")
class TestGetAiExplanations(TransactionCase):
    """Integration tests for `ir.model.get_ai_explanations`."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrModel = cls.env["ir.model"]
        cls.Registry = cls.env["ai.view.registry"]

    def _ensure_registry_entry(self, model_name, active=True):
        ir_model = self.IrModel._get(model_name)
        rec = self.Registry.with_context(active_test=False).search(
            [("model_id", "=", ir_model.id), ("view_type", "=", "form"),
             ("view_id", "=", False)], limit=1,
        )
        if rec:
            rec.active = active
            return rec
        return self.Registry.create({
            "model_id": ir_model.id,
            "view_type": "form",
            "active": active,
            "priority": 10,
        })

    def test_monkey_patch_applied(self):
        """Every model must expose `_explanation` thanks to the __init__ patch."""
        self.assertTrue(hasattr(models.Model, "_explanation"))
        self.assertIsNone(models.Model._explanation)
        self.assertIsNone(self.env["res.partner"]._explanation)

    def test_whitelist_respected(self):
        """Models absent from ai.view.registry are filtered out."""
        self._ensure_registry_entry("res.partner", active=True)
        # An active model with no `_explanation` returns nothing sensible,
        # so force a Python-level attribute just for this test.
        type(self.env["res.partner"])._explanation = (
            "[en_US]Contact record.[/en_US]"
        )
        try:
            result = self.IrModel.get_ai_explanations(
                model_names=["res.partner", "ir.rule"], lang="en_US",
            )
        finally:
            del type(self.env["res.partner"])._explanation
        # ir.rule is not in the registry → must be absent from the payload.
        self.assertNotIn("ir.rule", result)
        self.assertEqual(result.get("res.partner"), "Contact record.")

    def test_lang_default_fallback(self):
        """Missing `lang` argument falls back to env.lang or en_US."""
        self._ensure_registry_entry("res.partner", active=True)
        type(self.env["res.partner"])._explanation = (
            "[bg_BG]Партньор.[/bg_BG][en_US]Partner.[/en_US]"
        )
        try:
            result_bg = self.IrModel.with_context(lang="bg_BG") \
                .get_ai_explanations(model_names=["res.partner"])
            result_en = self.IrModel.with_context(lang="en_US") \
                .get_ai_explanations(model_names=["res.partner"])
        finally:
            del type(self.env["res.partner"])._explanation
        self.assertEqual(result_bg.get("res.partner"), "Партньор.")
        self.assertEqual(result_en.get("res.partner"), "Partner.")

    def test_inactive_registry_entry_skipped(self):
        self._ensure_registry_entry("res.partner", active=False)
        type(self.env["res.partner"])._explanation = (
            "[en_US]Contact.[/en_US]"
        )
        try:
            result = self.IrModel.get_ai_explanations(
                model_names=["res.partner"], lang="en_US",
            )
        finally:
            del type(self.env["res.partner"])._explanation
        self.assertNotIn("res.partner", result)
