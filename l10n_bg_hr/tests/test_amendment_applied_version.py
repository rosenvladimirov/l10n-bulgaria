"""ДС-то сочи версията, която е родило — иначе справките четат старото.

`version_id` е версията, КОЯТО ДС-то изменя. Версията, която активирането
РАЖДА, дотук не се записваше никъде, тъй че НАП експортът и ЕТЗ уведомлението
се градяха от изходната и описваха състоянието ПРЕДИ споразумението —
включително заплатата, която ДС-то е записало вярно.

Мутационна проверка (21.08.2026): без `self.applied_version_id = new_version`
в `_apply_version_changes` тестът пада на първата проверка (Falsy поле).
"""
from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAmendmentAppliedVersion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Приложена Версия",
        })
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 1000.0})

    def _approved_amendment(self):
        amd = self.env["l10n_bg.hr.version.amendment"].create({
            "version_id": self.version.id,
            "amendment_type": "wage_change",
            "date_signed": date(2026, 2, 1),
            "date_effective": date(2026, 3, 1),
            "subject": "Тест приложена версия",
            "new_wage": 2000.0,
        })
        amd.action_submit_for_approval()
        amd.action_approve()
        return amd

    def test_unactivated_amendment_falls_back_to_source(self):
        """Преди активиране бланката трябва да може да се печата — от изходната."""
        amd = self._approved_amendment()
        self.assertFalse(
            amd.applied_version_id,
            "неактивирано ДС не бива да сочи приложена версия")
        self.assertEqual(
            amd._l10n_bg_effective_version(), amd.version_id,
            "без приложена версия справката трябва да пада на изходната")

    def test_activation_records_the_born_version(self):
        """След активиране справките четат родената версия, не изходната."""
        amd = self._approved_amendment()
        izhodna = amd.version_id
        amd.action_activate()

        self.assertTrue(
            amd.applied_version_id,
            "активирането не е записало родената версия — всяка справка ще "
            "продължи да чете състоянието преди споразумението")
        self.assertNotEqual(
            amd.applied_version_id, izhodna,
            "приложената версия не бива да е изходната")

        # Същината: числото, което справката ще прочете.
        self.assertEqual(
            amd.applied_version_id.wage, 2000.0,
            "родената версия не носи договорената заплата")
        self.assertEqual(
            izhodna.wage, 1000.0,
            "изходната версия не бива да се мени — тя е историята")
        self.assertEqual(
            amd._l10n_bg_effective_version(), amd.applied_version_id,
            "справката още сочи изходната версия")

    def test_applied_version_is_not_copied(self):
        """Дубликат на ДС не наследява чужда приложена версия."""
        amd = self._approved_amendment()
        amd.action_activate()
        kopie = amd.copy()
        self.assertFalse(
            kopie.applied_version_id,
            "копието носи приложената версия на оригинала — ще опише чуждо "
            "състояние като свое")
