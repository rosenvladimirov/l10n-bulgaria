# -*- coding: utf-8 -*-
"""DEF-116 т.1в и т.1г — типове без съдържание и резюме, което не знае за графика.

т.1в: `vals` в ``_apply_version_changes`` се пълни само от заплата, длъжност,
квалификационна група, икономическа дейност, тип работно време, работно място,
дни отпуск и календар. Нито описанието, нито крайната дата влизат в него, а
отдолу стои отказ при празен `vals`. Следствие: „Друго“, „Допълнителни
задължения“ и „Удължаване на срока“ не можеха да влязат в сила при никакви
обстоятелства. Изиграно от Пламена с ДС 354.

При „Удължаване на срока“ е по-тежко: срокът не се записваше НИКЪДЕ — типът
съществува, приема данни и не удължава нищо.

т.1г: резюмето изброяваше шест величини без графика, който стана носител на
работното време. ДС 348 и 346 менят само графика и дават празно резюме — и на
екрана, и на хартията.
"""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTypesWithoutContent(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Празни Типове",
            "company_id": cls.env.company.id,
            "date_version": "2026-01-01",
        })
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 1000.0})

    def _ds(self, **vals):
        amd = self.env["l10n_bg.hr.version.amendment"].create(dict({
            "version_id": self.version.id,
            "date_signed": date(2026, 8, 1),
            "date_effective": date(2026, 9, 1),
            "subject": "Тест",
        }, **vals))
        amd.action_submit_for_approval()
        amd.action_approve()
        return amd

    def test_other_with_a_description_can_take_effect(self):
        """🚨 „Друго“ с описание вече влиза в сила."""
        amd = self._ds(amendment_type="other",
                       description="Уговорка за дистанционна работа")
        amd.action_activate()
        self.assertEqual(
            amd.state, "active",
            "типът „Друго“ още не може да влезе в сила при никакви "
            "обстоятелства")

    def test_a_textual_amendment_does_not_spawn_a_version(self):
        """🔑 Не се ражда версия — няма променена стойност, която да опише.

        Раждането ѝ би разцепило месеца във фиша за нищо.
        """
        predi = len(self.employee.version_ids)
        amd = self._ds(amendment_type="additional_duties",
                       description="Поема и касовата отчетност")
        amd.action_activate()
        self.assertEqual(
            len(self.employee.version_ids), predi,
            "текстово споразумение роди нова версия без нито една промяна")
        self.assertTrue(amd.applied_version_id)

    def test_a_textual_amendment_leaves_a_trace(self):
        """Следата отива в чатъра на действащата версия."""
        amd = self._ds(amendment_type="other", description="Уговорено X")
        amd.action_activate()
        tekstove = " ".join(m.body or "" for m in amd.applied_version_id.message_ids)
        self.assertIn("Уговорено X", tekstove)

    def test_a_textual_type_without_a_description_is_still_refused(self):
        """🚨 Регресия: празно споразумение си остава отказ.

        Гардът пази от подписан документ, който системата смята за приложен, а
        по договора нищо не е сменено.
        """
        amd = self._ds(amendment_type="other")
        with self.assertRaises(ValidationError):
            amd.action_activate()

    def test_contract_extension_writes_the_term(self):
        """🚨 Типът приемаше дата и не удължаваше нищо.

        ⚖️ Записва се СРОКЪТ, не прекратяването: чл. 68 КТ дава уговорен срок,
        който може да изтече без някой да прекрати, и тогава чл. 69, ал. 1
        действа сам.
        """
        amd = self._ds(amendment_type="contract_extension",
                       date_end=date(2027, 3, 31))
        amd.action_activate()
        rodena = amd.applied_version_id
        self.assertEqual(
            rodena.l10n_bg_fixed_term_end, date(2027, 3, 31),
            "удължаването не стигна до срока на договора")
        self.assertFalse(
            rodena.contract_date_end,
            "удължаването е записано като ПРЕКРАТЯВАНЕ — срокът не е краят")


@tagged("post_install", "-at_install")
class TestAmendmentSummary(TransactionCase):
    """т.1г — резюмето се чете на екрана и на хартията."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Резюме",
            "company_id": cls.env.company.id,
            "date_version": "2026-01-01",
        })
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 1517.60})
        cls.kalendar = cls.env["resource.calendar"].search([], limit=1)
        cls.drug = cls.env["resource.calendar"].create({
            "name": "График DEF116 — 4 часа",
            "hours_per_day": 4.0,
        })

    def _ds(self, **vals):
        return self.env["l10n_bg.hr.version.amendment"].create(dict({
            "version_id": self.version.id,
            "amendment_type": "other",
            "date_signed": date(2026, 8, 1),
            "date_effective": date(2026, 9, 1),
            "subject": "Тест резюме",
        }, **vals))

    def test_equal_values_are_not_reported_as_a_change(self):
        """🚨 ДС 344 пишеше „Заплата: 1517.60 → 1517.60“."""
        amd = self._ds(old_wage=1517.60, new_wage=1517.60)
        self.assertNotIn(
            "1517", amd.get_amendment_summary(),
            "резюмето отчита промяна там, където няма")

    def test_a_schedule_only_amendment_is_not_empty(self):
        """🚨 ДС 348 и 346 менят само графика и даваха празно резюме."""
        amd = self._ds(old_resource_calendar_id=self.kalendar.id,
                       new_resource_calendar_id=self.drug.id)
        rezyume = amd.get_amendment_summary()
        self.assertTrue(
            rezyume, "ДС само за график дава празно резюме — и на хартията")
        self.assertIn(self.drug.name, rezyume)

    def test_selection_values_print_their_label(self):
        """🚨 „Работно време: full_time → part_time“ вместо етикетите.

        Етикетът минава през превод, техническата стойност — не; на хартията
        излизаше английски идентификатор.
        """
        amd = self._ds(old_working_time_type="full_time",
                       new_working_time_type="part_time")
        rezyume = amd.get_amendment_summary()
        self.assertNotIn("part_time", rezyume)
        self.assertNotIn("full_time", rezyume)
