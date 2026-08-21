"""Командироването свършва — и оставя следа в историята.

Три дупки, които се държаха взаимно:
· визардът не пълнеше `is_temporary` / `is_temporary_assignment` / `date_end`,
  тъй че ДС от него раждаше ПОСТОЯННА версия;
· гардът затова блокираше срочните само през ФОРМАТА — един бизнес факт, два
  различни изхода;
· изтичащият крон пишеше ВЪРХУ изходната версия, тоест командироването
  изчезваше от историята, сякаш никога не е било.

Сега изходът ражда нова версия от `date_end + 1`, симетрично на входа.
"""
from datetime import date
from unittest.mock import patch

from odoo import fields as odoo_fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTemporaryAssignment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_staro = cls.env["hr.job"].create({"name": "Склададжия"})
        cls.job_novo = cls.env["hr.job"].create({"name": "Шофьор временно"})
        cls.employee = cls.env["hr.employee"].create({"name": "Тест Командировка"})
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 1000.0, "job_id": cls.job_staro.id})

    def _wizard(self, **vals):
        return self.env["l10n_bg.hr.version.amendment.wizard"].create(dict({
            "version_id": self.version.id,
            "employee_id": self.employee.id,
            "amendment_type": "temporary_assignment",
            "subject": "Временно преместване",
            # 🔑 Визардът слага ДНЕШНА дата на подписване, тъй че влизането в
            # сила трябва да е напред — иначе валидацията „подпис не може да е
            # след влизане в сила" гърми преди самата проверка.
            "date_effective": date(2099, 3, 1),
            "new_position_id": False,
        }, **vals))

    def test_wizard_fills_the_temporary_flags(self):
        """ДС от визарда носи флаговете и крайната дата."""
        wiz = self._wizard(date_end=date(2099, 5, 31))
        wiz.action_create_amendment()
        amd = self.env["l10n_bg.hr.version.amendment"].search(
            [("version_id", "=", self.version.id)], order="id desc", limit=1)
        self.assertTrue(
            amd.is_temporary and amd.is_temporary_assignment,
            "ДС-то от визарда не е срочно — изтичащият крон няма да го види и "
            "командироването няма да свърши никога")
        self.assertEqual(amd.date_end, date(2099, 5, 31))

    def test_wizard_refuses_temporary_without_end_date(self):
        """Без крайна дата визардът отказва."""
        wiz = self._wizard(date_end=False)
        with self.assertRaises(ValidationError):
            wiz.action_create_amendment()

    def test_temporary_amendment_can_be_activated(self):
        """Гардът падна: срочното ДС вече минава и през двата пътя."""
        amd = self.env["l10n_bg.hr.version.amendment"].create({
            "version_id": self.version.id,
            "amendment_type": "temporary_assignment",
            "date_signed": date(2026, 2, 1),
            "date_effective": date(2026, 3, 1),
            "date_end": date(2026, 5, 31),
            "is_temporary": True,
            "is_temporary_assignment": True,
            "subject": "Временно",
            "new_job_id": self.job_novo.id,
        })
        amd.action_submit_for_approval()
        amd.action_approve()
        amd.action_activate()
        self.assertEqual(amd.state, "active")
        self.assertEqual(amd.applied_version_id.job_id, self.job_novo)

    def test_expiry_creates_a_closing_version(self):
        """Изтичането ражда НОВА версия от date_end + 1 със старата длъжност."""
        amd = self.env["l10n_bg.hr.version.amendment"].create({
            "version_id": self.version.id,
            "amendment_type": "temporary_assignment",
            "date_signed": date(2026, 2, 1),
            "date_effective": date(2026, 3, 1),
            "date_end": date(2026, 5, 31),
            "is_temporary": True,
            "is_temporary_assignment": True,
            "subject": "Временно",
            "new_job_id": self.job_novo.id,
        })
        amd.action_submit_for_approval()
        amd.action_approve()
        amd.action_activate()

        with patch.object(odoo_fields.Date, "today",
                          staticmethod(lambda *a, **k: date(2026, 6, 15))):
            self.env["l10n_bg.hr.version.amendment"] \
                .cron_expire_temporary_amendments()

        self.assertEqual(amd.state, "expired")
        # Периодът на командироването остава описан: версията от 01.03 носи
        # новата длъжност, а тази от 01.06 връща старата.
        v_april = self.employee._get_version(date(2026, 4, 15))
        v_yuni = self.employee._get_version(date(2026, 6, 15))
        self.assertEqual(
            v_april.job_id, self.job_novo,
            "периодът на командироването е изгубил длъжността си")
        self.assertEqual(
            v_yuni.job_id, self.job_staro,
            "командироването не е свършило — длъжността не е върната")
        self.assertNotEqual(
            v_yuni, self.version,
            "изтичането е презаписало ИЗХОДНАТА версия вместо да роди нова")
