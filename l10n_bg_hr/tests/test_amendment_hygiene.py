"""П2 (хигиена на състоянието) и П3 (изборът на календар).

П3: изборът сумираше присъствията сурово, включително редовете с
`day_period='lunch'`. Стоковият календар носи пет обедни реда 12:00–13:00, тъй
че сборът излизаше 45 при договорени 40 и ДС за ПЪЛНО работно време се
ОТКАЗВАШЕ — а текстът на отказа тласкаше ТРЗ-то да трие обедните редове.

🆕 DEF-116/1б (01.09.2026): ДС-то вече не ОТГАТВА календар по две числа —
носи `new_resource_calendar_id` изрично. Тестовете тук минаха от „познава ли
верния календар" към „прилага ли избрания и извежда ли часовете от него".
Обедните редове остават във фикстурата, защото проверката за съгласуваност
още стъпва на `_get_hours_per_week()`.

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
        """Обедните редове не бива да провалят проверката за съгласуваност."""
        self.assertAlmostEqual(
            sum(a.hour_to - a.hour_from
                for a in self.kalendar_40.attendance_ids), 45.0, places=2,
            msg="фикстурата вече не възпроизвежда суровия сбор 45 — пренапиши я")
        self.assertAlmostEqual(
            self.kalendar_40._get_hours_per_week(), 40.0, places=2)

        amd = self._approve(self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "full_time",
            "new_resource_calendar_id": self.kalendar_40.id,
        }))
        amd.action_activate()  # не бива да хвърля
        self.assertEqual(
            amd.applied_version_id.resource_calendar_id, self.kalendar_40,
            "приложен е друг график, не избраният")

    def test_version_hours_follow_the_chosen_schedule(self):
        """Часовете на версията се ИЗВЕЖДАТ от графика, не се наследяват.

        Без този блок новата версия копира 40 ч от старата, докато графикът
        ѝ казва 20 — точно противоречието, което вторият клон на
        `_l10n_bg_mod_prorata` е построен да ЛОВИ. Мутация: махни блока в
        `_apply_version_changes` → пада.
        """
        redove = []
        for den in range(5):
            redove.append((0, 0, {
                "name": "Половин ден", "dayofweek": str(den),
                "hour_from": 8.0, "hour_to": 12.0, "day_period": "morning"}))
        kalendar_20 = self.env["resource.calendar"].create({
            "name": "Тест непълно 20ч", "hours_per_day": 4.0,
            "attendance_ids": redove,
        })
        self.version.write({"l10n_bg_weekly_hours": 40.0,
                            "l10n_bg_daily_hours": 8.0})
        amd = self._approve(self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "part_time",
            "new_resource_calendar_id": kalendar_20.id,
        }))
        amd.action_activate()
        nova = amd.applied_version_id
        self.assertEqual(nova.resource_calendar_id, kalendar_20)
        self.assertAlmostEqual(
            nova.l10n_bg_daily_hours, 4.0, places=2,
            msg="дневните часове са наследени от старата версия, а не "
                "изведени от графика")
        self.assertAlmostEqual(
            nova.l10n_bg_weekly_hours, 20.0, places=2,
            msg="седмичните часове застояха на 40 при график от 20 — това е "
                "противоречието, което прората после трябва да лови")

    def test_working_time_change_without_schedule_is_refused(self):
        """Без избран график ДС-то се отказва, вместо да гадае.

        🔑 Отказът идва при ПОДАВАНЕТО, не при активирането (DEF-175а). Дотук
        проверката се викаше чак от прилагането, тъй че потребителят минаваше
        три състояния и се удряше в стената без път назад.
        """
        amd = self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "part_time",
        })
        with self.assertRaises(ValidationError):
            amd.action_submit_for_approval()

    def test_internally_inconsistent_schedule_is_refused(self):
        """4 ч/ден при присъствия 08:00–17:00 е капан, не график.

        Фишът дели 168 ÷ 4 и дава 42 отработени дни в месец с 21. Изборът по
        едно число би го пропуснал — затова се сверява и сборът.
        """
        redove = []
        for den in range(5):
            redove.append((0, 0, {
                "name": "Цял ден", "dayofweek": str(den),
                "hour_from": 8.0, "hour_to": 17.0, "day_period": "morning"}))
        kapan = self.env["resource.calendar"].create({
            "name": "График непълно раб.време - 4ч.",
            "attendance_ids": redove,
        })
        # 🚨 `hours_per_day` е STORED COMPUTE от присъствията
        # (`_compute_hours_per_day` зависи от `attendance_ids`). Подаден при
        # СЪЗДАВАНЕТО, той се презаписва — 4,00 става 9,00, календарът излиза
        # вътрешно СЪГЛАСУВАН и гардът правилно мълчи. Тоест капанът не ловеше
        # и тестът не проверяваше нищо.
        #
        # Полето е `readonly=False`, тъй че отделен запис СЛЕД създаването се
        # задържа: присъствията не се менят, компютът не се преизчислява.
        # 🔑 DEF-175: ДС-то стига до одобрено с ЗДРАВ календар, и чак после
        # някой разваля графика. Инак ранната преграда (при подаването) го
        # хваща първа и тази проверка не мери нищо — тя пази ДРУГО: анекс,
        # стигнал до одобрен без бутона (импорт, RPC), както казва и
        # `test_late_guard_still_stands`.
        amd = self._approve(self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "part_time",
            "new_resource_calendar_id": kapan.id,
        }))
        kapan.hours_per_day = 4.0
        self.assertAlmostEqual(
            kapan.hours_per_day, 4.0, places=2,
            msg="капанът пак се нормализира — тестът не проверява нищо")
        with self.assertRaises(ValidationError):
            amd.action_activate()

    def test_flexible_schedule_is_accepted_without_deriving_hours(self):
        """Гъвкавият график няма присъствия — приема се, но не дава часове."""
        gavkav = self.env["resource.calendar"].create({
            "name": "Тест гъвкав", "flexible_hours": True, "hours_per_day": 8.0,
        })
        amd = self._approve(self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "flexible",
            "new_resource_calendar_id": gavkav.id,
        }))
        amd.action_activate()  # не бива да хвърля
        self.assertEqual(amd.applied_version_id.resource_calendar_id, gavkav)

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
        # 🔑 Търси се ДАТАТА, не английска дума: съобщението минава през превод
        # и на българска база думата „early" я няма. Тестът падаше не защото
        # следата липсва, а защото е на друг език.
        self.assertIn(
            str(amd.date_effective), telata,
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

    # =========================================================================
    # DEF-175 — ГАРДЪТ ГЪРМИ ТАМ, КЪДЕТО ОЩЕ МОЖЕ ДА СЕ ПОПРАВИ
    # =========================================================================

    def test_missing_schedule_is_refused_before_approval(self):
        """Отказът идва при ПОДАВАНЕТО, не три състояния по-късно.

        Дотук проверката се викаше само от `_apply_version_changes`. Човекът
        минаваше чернова → за одобрение → одобрено → в сила и получаваше
        отказа накрая, когато документът вече е подписан — а връщане назад по
        машината на състоянията няма.

        Мутация: махни викането от `action_submit_for_approval` → пада,
        защото подаването минава без възражение.
        """
        amd = self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "part_time",
        })
        with self.assertRaises(ValidationError):
            amd.action_submit_for_approval()
        self.assertEqual(
            amd.state, "draft",
            "ДС-то е сменило състояние въпреки отказа — точно капанът, от "
            "който няма връщане")

    def test_inconsistent_schedule_is_refused_before_approval(self):
        """Противоречивият график също се хваща рано."""
        redove = []
        for den in range(5):
            redove.append((0, 0, {
                "name": "Цял ден", "dayofweek": str(den),
                "hour_from": 8.0, "hour_to": 17.0, "day_period": "morning"}))
        kapan = self.env["resource.calendar"].create({
            "name": "График непълно раб.време - 4ч.",
            "attendance_ids": redove,
        })
        # 🚨 `hours_per_day` е STORED COMPUTE от присъствията
        # (`_compute_hours_per_day` зависи от `attendance_ids`). Подаден при
        # СЪЗДАВАНЕТО, той се презаписва — 4,00 става 9,00, календарът излиза
        # вътрешно СЪГЛАСУВАН и гардът правилно мълчи. Тоест капанът не ловеше
        # и тестът не проверяваше нищо.
        #
        # Полето е `readonly=False`, тъй че отделен запис СЛЕД създаването се
        # задържа: присъствията не се менят, компютът не се преизчислява.
        kapan.hours_per_day = 4.0
        self.assertAlmostEqual(
            kapan.hours_per_day, 4.0, places=2,
            msg="капанът пак се нормализира — тестът не проверява нищо")
        amd = self._amendment({
            "amendment_type": "working_time_change",
            "new_working_time_type": "part_time",
            "new_resource_calendar_id": kapan.id,
        })
        with self.assertRaises(ValidationError):
            amd.action_submit_for_approval()

    def test_late_guard_still_stands(self):
        """Ранната проверка НЕ заменя късната.

        Импортът и RPC не минават през бутона за подаване; гардът в
        прилагането остава последната преграда.
        """
        amd = self._approve(self._amendment({
            "amendment_type": "wage_change", "new_wage": 1200.0,
        }))
        # тип работно време се сменя ПОСЛЕ, заобикаляйки ранната проверка
        amd.new_working_time_type = "part_time"
        with self.assertRaises(ValidationError):
            amd.action_activate()

