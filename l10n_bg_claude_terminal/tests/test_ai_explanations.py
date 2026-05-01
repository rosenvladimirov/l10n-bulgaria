# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.ir_model import _extract_lang


@tagged("post_install", "-at_install")
class TestExtractLang(TransactionCase):
    """Unit tests for the language-filtering parser (identical to 18/19)."""

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
class TestGetAiExplanations16(TransactionCase):
    """Integration tests for the 16.0 variant — ``model_names`` is required."""

    def test_monkey_patch_applied(self):
        self.assertTrue(hasattr(models.Model, "_explanation"))
        self.assertIsNone(models.Model._explanation)
        self.assertIsNone(self.env["res.partner"]._explanation)

    def test_model_names_required(self):
        """Without ai.view.registry there is no whitelist → must raise."""
        with self.assertRaises(UserError):
            self.env["ir.model"].get_ai_explanations(lang="en_US")

    def test_explicit_model_names(self):
        type(self.env["res.partner"])._explanation = (
            "[bg_BG]Партньор.[/bg_BG][en_US]Partner.[/en_US]"
        )
        try:
            bg = self.env["ir.model"].get_ai_explanations(
                model_names=["res.partner"], lang="bg_BG",
            )
            en = self.env["ir.model"].get_ai_explanations(
                model_names=["res.partner"], lang="en_US",
            )
            de = self.env["ir.model"].get_ai_explanations(
                model_names=["res.partner"], lang="de_DE",
            )
        finally:
            del type(self.env["res.partner"])._explanation
        self.assertEqual(bg.get("res.partner"), "Партньор.")
        self.assertEqual(en.get("res.partner"), "Partner.")
        self.assertNotIn("res.partner", de)
