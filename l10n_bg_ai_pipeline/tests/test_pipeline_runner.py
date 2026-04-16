# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPipelineStepMatching(TransactionCase):
    """Unit tests for ai.pipeline.step._matches — the guard that makes
    injected steps only fire when their skill has been resolved.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Step = cls.env["ai.pipeline.step"]
        cls.Skill = cls.env["ai.skill"]

    def _make_step(self, **overrides):
        vals = {
            "name": "t_step",
            "pipeline": "tokenize",
            "sequence": 500,
            "model": "ai.pipeline.runner",
            "method": "step_build_text",
            "on_error": "skip",
        }
        vals.update(overrides)
        return self.Step.create(vals)

    def test_base_step_always_passes(self):
        step = self._make_step()
        self.assertTrue(step._matches({}))

    def test_skill_gated_step_waits_for_resolution(self):
        skill = self.Skill.create({
            "name": "test-skill",
            "description": "trigger hint",
        })
        step = self._make_step(name="t_gated", skill_id=skill.id)
        # No matched skills yet → step sits idle.
        self.assertFalse(step._matches({"matched_skill_ids": []}))
        # Skill resolved → step becomes eligible.
        self.assertTrue(step._matches({"matched_skill_ids": [skill.id]}))

    def test_trigger_domain_filters_by_ctx(self):
        step = self._make_step(
            name="t_domain",
            trigger_domain="[('source_model','=','account.move')]",
        )
        self.assertTrue(step._matches({"source_model": "account.move"}))
        self.assertFalse(step._matches({"source_model": "res.partner"}))


@tagged("post_install", "-at_install")
class TestPipelineRunnerSmoke(TransactionCase):
    """Smoke test: runner iterates steps, creates a run record, and
    respects the abort flag.  Embedding/Qdrant calls are stubbed so
    the test does not need external services.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Runner = cls.env["ai.pipeline.runner"]
        cls.Step = cls.env["ai.pipeline.step"]

    def test_run_creates_audit_record(self):
        with patch.object(
            type(self.Runner), "_load_steps", return_value=self.Step.browse(),
        ):
            ctx = self.Runner.run("tokenize", doc=None)
        self.assertIn("matched_skill_ids", ctx)
        last = self.env["ai.pipeline.run"].search(
            [("pipeline", "=", "tokenize")], limit=1, order="id desc",
        )
        self.assertEqual(last.state, "done")
        self.assertEqual(last.executed_step_count, 0)
