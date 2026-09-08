# -*- coding: utf-8 -*-
"""DEF-175б — от гардовете имаше отказ, но нямаше връщане.

Изиграно от Пламена: ДС 345 е създадено без график, подадено, одобрено — и чак
при активирането отказа. После графикът е попълнен, активирането пак пада, този
път по друга причина, и остава само отказът. Всяка засечка значи НОВО ДС с нов
номер по същия подписан документ, а ``ir.sequence`` не се връща.

Гардовете вече отказват рано (DEF-175а). Без път назад ранният отказ само мести
задънената улица по-напред.
"""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAmendmentWayBack(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Връщане В Чернова",
            "company_id": cls.env.company.id,
            "date_version": "2026-01-01",
        })
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 1000.0})

    def _ds(self):
        return self.env["l10n_bg.hr.version.amendment"].create({
            "version_id": self.version.id,
            "amendment_type": "wage_change",
            "date_signed": date(2026, 8, 1),
            "date_effective": date(2026, 9, 1),
            "subject": "Тест връщане",
            "new_wage": 1200.0,
        })

    def test_submitted_can_go_back(self):
        """🚨 Същината: подадено ДС се връща за поправка."""
        amd = self._ds()
        amd.action_submit_for_approval()
        self.assertEqual(amd.state, "to_approve")
        amd.action_draft()
        self.assertEqual(
            amd.state, "draft",
            "няма връщане от подадено — засечката иска ново ДС с нов номер")

    def test_approved_can_go_back(self):
        amd = self._ds()
        amd.action_submit_for_approval()
        amd.action_approve()
        amd.action_draft()
        self.assertEqual(amd.state, "draft")

    def test_cancelled_can_go_back(self):
        """Отказаното също — точно случаят на ДС 345."""
        amd = self._ds()
        amd.action_cancel()
        self.assertEqual(amd.state, "cancel")
        amd.action_draft()
        self.assertEqual(amd.state, "draft")

    def test_the_return_leaves_a_trace(self):
        """Връщането е събитие по документа, не тихо превключване."""
        amd = self._ds()
        amd.action_submit_for_approval()
        broy = len(amd.message_ids)
        amd.action_draft()
        self.assertGreater(
            len(amd.message_ids), broy,
            "връщането в чернова не остави следа в чатъра")

    def test_active_cannot_go_back(self):
        """🚨 Регресия: в сила НЕ се връща.

        Подписаният документ би се разминал с версията, която е родил — точно
        каквото гардът в ``write`` пази.
        """
        amd = self._ds()
        amd.action_submit_for_approval()
        amd.action_approve()
        amd.action_activate()
        self.assertEqual(amd.state, "active")
        with self.assertRaises(ValidationError):
            amd.action_draft()

    def test_draft_is_a_no_op(self):
        """Връщане от чернова не гърми и не пише в чатъра."""
        amd = self._ds()
        broy = len(amd.message_ids)
        amd.action_draft()
        self.assertEqual(amd.state, "draft")
        self.assertEqual(len(amd.message_ids), broy)
