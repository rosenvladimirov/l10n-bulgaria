# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAiSkillMatch(TransactionCase):
    """Semantic match returns skills in Qdrant score order,
    honours the language filter, and silently drops missing ids.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Skill = cls.env["ai.skill"]

    def test_match_for_vector_preserves_score_order(self):
        a = self.Skill.create({
            "name": "skill-a", "description": "A",
        })
        b = self.Skill.create({
            "name": "skill-b", "description": "B",
        })
        fake_hits = [
            {"payload": {"res_id": b.id}, "score": 0.91},
            {"payload": {"res_id": a.id}, "score": 0.72},
        ]
        with patch.object(
            type(self.env["ai.qdrant.skills.client"]),
            "search", return_value=fake_hits,
        ):
            recs, scores = self.Skill.match_for_vector([0.1] * 4)
        self.assertEqual(recs.ids, [b.id, a.id])
        self.assertEqual(scores, [0.91, 0.72])

    def test_match_for_vector_filters_by_language(self):
        s_any = self.Skill.create({
            "name": "skill-any", "description": "any",
        })  # language defaults to 'all'
        s_bg = self.Skill.create({
            "name": "skill-bg", "description": "bg", "language": "bg_BG",
        })
        s_en = self.Skill.create({
            "name": "skill-en", "description": "en", "language": "en_US",
        })
        fake_hits = [
            {"payload": {"res_id": s_any.id}, "score": 0.95},
            {"payload": {"res_id": s_bg.id}, "score": 0.88},
            {"payload": {"res_id": s_en.id}, "score": 0.80},
        ]
        with patch.object(
            type(self.env["ai.qdrant.skills.client"]),
            "search", return_value=fake_hits,
        ):
            recs, _ = self.Skill.match_for_vector([0.1] * 4, lang="bg_BG")
        self.assertEqual(set(recs.ids), {s_any.id, s_bg.id})
