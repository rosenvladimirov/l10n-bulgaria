# -*- coding: utf-8 -*-
"""DEF-174 — табът „Временно преместване“ не беше сверен с чл. 120 КТ.

Четири полета без нито един четец. Грепнат целият стек — само дефиницията,
изгледът и една валидация. Нищо от тях не влизаше във версията, в бланка или в
декларация. Особено възнаграждението при преместване е Monetary и изглежда точно
като онова по чл. 267, ал. 3, а не отиваше никъде.

Числата също не отговаряха на нормата. Валидацията беше до 12 МЕСЕЦА, докато
чл. 120, ал. 1 дава 45 КАЛЕНДАРНИ ДНИ през една календарна година, а при
престой — докато той продължава. Бележката в таба цитираше чл. 106-114; чл. 110
и чл. 111 са допълнителен труд по ОТДЕЛЕН трудов договор, не изменение на
съществуващото правоотношение.

И липсваше гардът, който ал. 1 иска: преместването е допустимо „в същото или в
друго предприятие, но в същото населено място или местност“.
"""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestArticle120(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Чл. 120",
            "company_id": cls.env.company.id,
        })
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 1000.0})
        cls.grad = cls.env["res.partner"].create({
            "name": "Адрес Пловдив", "city": "Пловдив"})
        cls.drug_grad = cls.env["res.partner"].create({
            "name": "Адрес Варна", "city": "Варна"})
        cls.mesto_tuk = cls.env["hr.work.location"].create({
            "name": "Цех 1", "company_id": cls.env.company.id,
            "address_id": cls.grad.id})
        cls.mesto_sasht = cls.env["hr.work.location"].create({
            "name": "Цех 2", "company_id": cls.env.company.id,
            "address_id": cls.grad.id})
        cls.mesto_drugade = cls.env["hr.work.location"].create({
            "name": "Склад Варна", "company_id": cls.env.company.id,
            "address_id": cls.drug_grad.id})

    def _premestvane(self, **vals):
        return self.env["l10n_bg.hr.version.amendment"].create(dict({
            "version_id": self.version.id,
            "amendment_type": "temporary_assignment",
            "is_temporary": True,
            "is_temporary_assignment": True,
            "date_signed": date(2026, 1, 10),
            "date_effective": date(2026, 2, 1),
            "date_end": date(2026, 3, 1),
            "subject": "Преместване",
            "temporary_assignment_reason": "production_necessity",
        }, **vals))

    def test_days_are_derived_from_the_dates(self):
        """🔑 Не второ поле — дните следват от датите.

        Мярката на чл. 120 е в календарни дни, а полето беше в месеци и се
        въвеждаше отделно от периода.
        """
        amd = self._premestvane()
        self.assertEqual(
            amd.l10n_bg_assignment_days, 29,
            "01.02–01.03.2026 включително са 29 календарни дни")

    def test_forty_five_days_is_the_cap(self):
        """🚨 Чл. 120, ал. 1 — 45 календарни дни, не 12 месеца."""
        with self.assertRaises(ValidationError):
            self._premestvane(date_end=date(2026, 4, 30))

    def test_the_cap_is_per_year_not_per_assignment(self):
        """🚨 Същината: таванът е за ГОДИНАТА.

        Три премествания по трийсет дни минаваха поединично и даваха деветдесет.
        """
        parvo = self._premestvane(date_end=date(2026, 2, 28))
        parvo.action_submit_for_approval()
        parvo.action_approve()
        self.assertEqual(parvo.l10n_bg_assignment_days, 28)
        with self.assertRaises(ValidationError):
            self._premestvane(date_effective=date(2026, 5, 1),
                              date_end=date(2026, 6, 15))

    def test_idle_time_has_no_cap(self):
        """⚖️ При престой ал. 1 казва „докато той продължава“."""
        amd = self._premestvane(temporary_assignment_reason="idle_time",
                                date_end=date(2026, 12, 31))
        self.assertGreater(amd.l10n_bg_assignment_days, 45)

    def test_the_same_settlement_passes(self):
        """Друго предприятие в същото населено място е допустимо."""
        amd = self._premestvane(
            old_work_location_id=self.mesto_tuk.id,
            new_work_location_id=self.mesto_sasht.id)
        self.assertTrue(amd.id)

    def test_another_settlement_is_refused(self):
        """🚨 Гардът, който липсваше изцяло."""
        with self.assertRaises(ValidationError):
            self._premestvane(
                old_work_location_id=self.mesto_tuk.id,
                new_work_location_id=self.mesto_drugade.id)

    def test_an_unknown_settlement_does_not_block(self):
        """🚨 Регресия: непопълнен адрес не е доказателство за нарушение."""
        bez_grad = self.env["hr.work.location"].create({
            "name": "Обект без адрес", "company_id": self.env.company.id})
        amd = self._premestvane(
            old_work_location_id=self.mesto_tuk.id,
            new_work_location_id=bez_grad.id)
        self.assertTrue(amd.id)

    def test_compensation_below_the_main_wage_is_refused(self):
        """⚖️ Чл. 267, ал. 3 — не по-малко от брутното за основната работа."""
        with self.assertRaises(ValidationError):
            self._premestvane(old_wage=1000.0, assignment_compensation=800.0)

    def test_compensation_reaches_the_version(self):
        """🚨 Полето стоеше без нито един четец."""
        amd = self._premestvane(old_wage=1000.0,
                                assignment_compensation=1300.0)
        amd.action_submit_for_approval()
        amd.action_approve()
        amd.action_activate()
        self.assertAlmostEqual(
            amd.applied_version_id.wage, 1300.0, places=2,
            msg="възнаграждението при преместване не стигна до версията")

    def test_two_sources_for_the_wage_are_refused(self):
        """🚨 Две твърдения за една стойност — изборът не е наш."""
        amd = self._premestvane(old_wage=1000.0,
                                assignment_compensation=1300.0,
                                new_wage=1400.0)
        amd.action_submit_for_approval()
        amd.action_approve()
        with self.assertRaises(ValidationError):
            amd.action_activate()
