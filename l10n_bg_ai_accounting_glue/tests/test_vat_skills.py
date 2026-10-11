# -*- coding: utf-8 -*-
"""Знание-skills за ДДС и локализацията (19.0.1.1.0): заредени, само знание,
с двуезично описание и съдържание на български, регистрирани в hooks."""
from odoo.tests import TransactionCase, tagged

from odoo.addons.l10n_bg_ai_accounting_glue.hooks import SKILL_XMLIDS

VAT_SKILLS = (
    "bg-l10n-accounting-map",
    "bg-vat-tax-repartition-tags",
    "bg-vat-document-type-protocols",
    "bg-vat-customs-import-base",
    "bg-vat-private-mixed-use",
    "bg-vat-ica-deferred-credit",
    "bg-vat-ledgers-closing",
    "bg-cita-expense-tax",
)


@tagged("post_install", "-at_install")
class TestVatSkills(TransactionCase):

    def test_vat_skills_are_loaded_as_knowledge_only(self):
        skills = self.env["ai.skill"].search([("name", "in", VAT_SKILLS)])
        self.assertEqual(sorted(skills.mapped("name")), sorted(VAT_SKILLS))
        for skill in skills:
            self.assertFalse(skill.resources_model, skill.name)
            self.assertFalse(skill.resources_method, skill.name)
            self.assertFalse(skill.pipeline_step_ids, skill.name)
            self.assertIn("[en_US]", skill.description, skill.name)
            self.assertIn("[bg_BG]", skill.description, skill.name)
            self.assertIn("[bg_BG]", skill.content or "", skill.name)
            self.assertTrue(skill.get_external_id()[skill.id].startswith(
                "l10n_bg_ai_accounting_glue."), skill.name)

    def test_every_module_skill_is_in_the_hooks(self):
        """Hook-ът и миграцията токенизират само изброените — нов skill без ред
        в SKILL_XMLIDS би останал draft завинаги."""
        # полето `module` не се попълва при зареждане от XML (двигателят го
        # пише в create, преди да има XML id) — затова през ir.model.data
        listed = {self.env.ref(xid).name for xid in SKILL_XMLIDS}
        res_ids = self.env["ir.model.data"].search([
            ("module", "=", "l10n_bg_ai_accounting_glue"), ("model", "=", "ai.skill"),
        ]).mapped("res_id")
        module_skills = self.env["ai.skill"].browse(res_ids)
        self.assertEqual(set(module_skills.mapped("name")), listed)

    def test_map_routes_to_every_vat_skill(self):
        content = self.env.ref("l10n_bg_ai_accounting_glue.skill_bg_l10n_accounting_map").content
        for name in VAT_SKILLS[1:]:
            self.assertIn(name, content)
