"""П2 (хигиена на състоянието) и П3 (изборът на календар).

П3: изборът сумираше присъствията сурово, включително редовете с
`day_period='lunch'`. Стоковият календар носи пет обедни реда 12:00–13:00, тъй
че сборът излизаше 45 при договорени 40 и ДС за ПЪЛНО работно време се
ОТКАЗВАШЕ — а текстът на отказа тласкаше ТРЗ-то да трие обедните редове.

П2: ДС без нито една промяна излизаше тихо и въпреки това ставаше „в сила";
приложено ДС можеше да се редактира и документът да се разминe с версията,
която е родил.
"""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAmendmentHygiene(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Тест Хигиена"})
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 1000.0})

        # Стоков календар: 40 работни часа + ПЕТ обедни реда по един час.
        # Суровият сбор е 45 — точно случаят, който блокираше активирането.
        redove = []
        for den in range(5):
            redove += [
                (0, 0, {"name": "Преди обед", "dayofweek": str(den),
                        "hour_from": 8.0, "hour_to": 12.0,
                        "day_period": "morning"}),
                (0, 0, {"name": "Обед", "dayofweek": str(den),
                        "hour_from": 12.0, "hour_to": 13.0,
                        "day_period": "lunch"}),
                (0, 0, {"name": "След обед", "dayofweek": str(den),
                        "hour_from": 13.0, "hour_to": 17.0,
                        "day_period": "afternoon"}),
            ]
        cls.kalendar_40 = cls.env["resource.calendar"].create({
            "name": "Тест пълно 40ч с обед",
            "hours_per_day": 8.0,
            "attendance_ids": redove,
        })

    def _amendment(self, vals):
        return self.env["l10n_bg.hr.version.amendment"].create(dict({
            "version_id": self.version.id,
            "date_signed": date(2026, 2, 1),
            "date_effective": date(2026, 3, 1),
            "subject": "Тест хигиена",
        }, **vals))

    def _approve(self, amd):
        amd.action_submit_for_approval()
        amd.action_approve()
        return amd

    # ---------------- П3 ----------------

    def test_lunch_rows_do_not_block_full_time(self):
        """Календар с обедни редове трябва да пасне на 40ч/8ч, не да отказва."""
        self.assertAlmostEqual(
            sum(a.hour_to - a.hour_from
                for a in self.kalendar_40.attendance_ids), 45.0, places=2,
            msg="фикстурата вече не възпроизвежда суровия сбор 45 — пренапиши я")
        self.assertAlmostEqual(
            self.kalendar_40._get_hours_per_week(), 40.0, places=2)

        amd = self._approve(self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "full_time",
            "new_weekly_hours": 40.0,
            "new_daily_hours": 8.0,
        }))
        amd.action_activate()  # не бива да хвърля
        izbran = amd.applied_version_id.resource_calendar_id
        self.assertTrue(izbran, "не е избран никакъв календар")
        # Кой точно запис е избран не е важно — може да има повече от един
        # подходящ. Важно е часовете му да са ДОГОВОРЕНИТЕ.
        self.assertAlmostEqual(izbran._get_hours_per_week(), 40.0, places=2)
        self.assertAlmostEqual(izbran._get_hours_per_day(), 8.0, places=2)

    def test_working_time_change_without_hours_is_refused(self):
        """Без нови часове ДС-то се отказва, вместо да потвърди заварените."""
        amd = self._approve(self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "part_time",
        }))
        with self.assertRaises(ValidationError):
            amd.action_activate()

    def test_flexible_calendar_is_not_picked(self):
        """Гъвкав календар няма съпоставими часове — не се избира."""
        self.env["resource.calendar"].create({
            "name": "Тест гъвкав",
            "flexible_hours": True,
            "hours_per_day": 8.0,
        })
        amd = self._approve(self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "full_time",
            "new_weekly_hours": 40.0,
            "new_daily_hours": 8.0,
        }))
        amd.action_activate()
        self.assertFalse(
            amd.applied_version_id.resource_calendar_id.flexible_hours,
            "избран е гъвкав календар")

    # ---------------- П2 ----------------

    def test_amendment_without_any_change_is_refused(self):
        """Празно ДС не бива да става „в сила“ мълчаливо."""
        amd = self._approve(self._amendment({"amendment_type": "other"}))
        with self.assertRaises(ValidationError):
            amd.action_activate()
        self.assertEqual(
            amd.state, "approved",
            "състоянието е вдигнато въпреки че нищо не е приложено")

    def test_applied_amendment_is_locked(self):
        """Приложено ДС не се редактира — документът е история."""
        amd = self._approve(self._amendment({
            "amendment_type": "wage_change", "new_wage": 2000.0,
        }))
        amd.action_activate()
        with self.assertRaises(ValidationError):
            amd.new_wage = 3000.0
        with self.assertRaises(ValidationError):
            amd.date_effective = date(2026, 4, 1)

    def test_service_fields_still_writable_when_applied(self):
        """Регистърът и подписът пишат по активно ДС — това е законно."""
        amd = self._approve(self._amendment({
            "amendment_type": "wage_change", "new_wage": 2000.0,
        }))
        amd.action_activate()
        amd.write({"description": "<p>бележка след прилагането</p>"})
        self.assertIn("бележка", amd.description)

    # ---------------- ADR-0006: кога може да се активира ----------------

    def test_activation_before_effective_date_is_refused(self):
        """Обикновеното активиране чака датата."""
        amd = self._approve(self._amendment({
            "amendment_type": "wage_change",
            "new_wage": 2000.0,
            "date_effective": date(2099, 1, 1),
        }))
        self.assertTrue(
            amd.l10n_bg_effective_in_future,
            "компютът не разпознава бъдеща дата — бутоните ще са грешните")
        with self.assertRaises(ValidationError):
            amd.action_activate()
        self.assertEqual(amd.state, "approved")

    def test_early_activation_passes_and_leaves_a_trace(self):
        """Предсрочното минава, но се записва в чатъра."""
        amd = self._approve(self._amendment({
            "amendment_type": "wage_change",
            "new_wage": 2000.0,
            "date_effective": date(2099, 1, 1),
        }))
        amd.action_activate_early()
        self.assertEqual(amd.state, "active")
        telata = " ".join(amd.message_ids.mapped("body") or [])
        self.assertIn(
            "early", telata.lower(),
            "предсрочното активиране не е оставило следа в чатъра")

    def test_activation_on_or_after_effective_date_passes(self):
        """Настъпило ДС минава по обикновения път — кронът върви оттам."""
        amd = self._approve(self._amendment({
            "amendment_type": "wage_change",
            "new_wage": 2000.0,
            "date_effective": date(2026, 3, 1),
        }))
        self.assertFalse(amd.l10n_bg_effective_in_future)
        amd.action_activate()
        self.assertEqual(amd.state, "active")

    def test_backdating_hook_exists_and_is_called(self):
        """Куката за затворен период се вика при всяко активиране.

        Тук се проверява само ДОГОВОРЪТ — самата проверка живее в слоя с
        ведомостта (ADR-0006), който базовият модул не познава.
        """
        amd = self._approve(self._amendment({
            "amendment_type": "wage_change", "new_wage": 2000.0,
        }))
        vikana = []
        original = type(amd)._l10n_bg_check_backdating

        def shpionin(zapis):
            vikana.append(zapis.id)
            return original(zapis)

        type(amd)._l10n_bg_check_backdating = shpionin
        try:
            amd.action_activate()
        finally:
            type(amd)._l10n_bg_check_backdating = original
        self.assertEqual(
            vikana, [amd.id],
            "куката не е извикана — слоят с ведомостта няма да може да откаже "
            "връщане назад в затворен период")
