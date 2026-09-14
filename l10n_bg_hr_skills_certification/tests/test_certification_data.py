# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Видовете сертификати носят умения и нива, а „Нов“ в Сертификати има от какво да избира.

Повод (Полигруп, 14.09.2026): без вид с отметка „Сертификат“ модалът на ядрото
(hr.employee.skill.open_hr_employee_skill_modal) взима празен вид, списъкът с умения
е празен и записът пада на NOT NULL за skill_id.
"""
from odoo.tests import TransactionCase, tagged

M = "l10n_bg_hr_skills_certification."


@tagged("post_install", "-at_install")
class TestCertificationData(TransactionCase):

    def test_each_type_is_a_certification_with_its_skills_and_levels(self):
        for xmlid, umenia, niva in (
            ("skill_type_electrical_safety", 1, 5),
            ("skill_type_welding", 3, 3),
            ("skill_type_forklift", 1, 3),
        ):
            vid = self.env.ref(M + xmlid)
            self.assertTrue(vid.is_certification, "%s не е отбелязан като сертификат" % xmlid)
            self.assertEqual((len(vid.skill_ids), len(vid.skill_level_ids)), (umenia, niva),
                             "%s: броят умения/нива не е по наредбата" % xmlid)
            self.assertEqual(len(vid.skill_level_ids.filtered("default_level")), 1,
                             "%s: трябва точно едно ниво по подразбиране" % xmlid)

    def test_levels_follow_the_regulation_order(self):
        # Нивата се подреждат по level_progress — редът е този на наредбите.
        vid = self.env.ref(M + "skill_type_electrical_safety")
        self.assertEqual(vid.skill_level_ids.mapped("level_progress"), [20, 40, 60, 80, 100])

    def test_the_certificate_modal_has_something_to_choose(self):
        deistvie = self.env["hr.employee.skill"].open_hr_employee_skill_modal()
        vid = self.env["hr.skill.type"].browse(deistvie["context"]["default_skill_type_id"])
        self.assertTrue(vid.is_certification,
                        "модалът няма вид сертификат — „Нов“ пак ще пише празен ред")
        sluzhitel = self.env["hr.employee"].create({"name": "Cert Test 1409"})
        red = self.env["hr.employee.skill"].create({
            "employee_id": sluzhitel.id,
            "skill_type_id": vid.id,
            "skill_id": vid.skill_ids[0].id,
            "skill_level_id": vid.skill_level_ids.filtered("default_level").id,
        })
        self.assertTrue(red.is_certification)
