"""Кронът активира ДС в реда, в който промените влизат в сила.

🔑 Защо тестът е построен така: ако ДВЕТЕ ДС носят заплата, грешният ред НЕ се
вижда — всяко ражда своята версия с новата стойност и числата излизат верни.
Дефектът излиза само когато ПО-КЪСНОТО ДС не пипа заплатата: тогава
`create_version` копира състоянието, действащо на неговата дата, а то е отпреди
по-ранното повишение ⇒ от по-късната дата заплатата се връща назад.

Мутационна проверка (20.08.2026): с `_order` на модела (`date_signed desc`) и без
`order=` в крона тестът пада с 1000.0 != 2000.0. С поправката минава.
"""
from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAmendmentActivationOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Активиране Ред",
        })
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 1000.0})

    def _amendment(self, signed, effective, vals=None):
        """Одобрено ДС върху изходната версия."""
        amd = self.env["l10n_bg.hr.version.amendment"].create(dict({
            "version_id": self.version.id,
            "amendment_type": "wage_change",
            "date_signed": signed,
            "date_effective": effective,
            "subject": "Тест",
        }, **(vals or {})))
        amd.action_submit_for_approval()
        amd.action_approve()
        return amd

    def test_cron_activates_in_effective_date_order(self):
        """По-късно ДС без заплата не бива да връща по-ранното повишение."""
        # Естественият случай: по-ранната промяна е подписана по-рано, тъй че
        # `date_signed desc` я слага ПОСЛЕДНА — точно обратното на нужното.
        rano = self._amendment(
            date(2026, 2, 1), date(2026, 3, 1), {"new_wage": 2000.0})
        # Промяна, която НЕ е заплата — само така се вижда дефектът: по-късната
        # версия копира състоянието отпреди повишението. (Текстово работно
        # място не става: то не е носител и ДС-то законно се отказва.)
        kasno = self._amendment(
            date(2026, 5, 1), date(2026, 6, 1), {
                "amendment_type": "leave_change",
                "new_leave_days": 25.0,
            })

        # Контрола, че подредбата на модела наистина е обратната — иначе
        # тестът минава по случайност и не доказва нищо.
        podreredeni = self.env["l10n_bg.hr.version.amendment"].search(
            [("id", "in", (rano | kasno).ids)])
        self.assertEqual(
            podreredeni.ids, (kasno | rano).ids,
            "_order на модела вече не е `date_signed desc` — тестът трябва да "
            "се пренапише, защото вече не възпроизвежда обратния ред.")

        with self._patch_today(date(2026, 7, 1)):
            self.env["l10n_bg.hr.version.amendment"].cron_activate_due_amendments()

        self.assertEqual(rano.state, "active")
        self.assertEqual(kasno.state, "active")

        # Същината: заплатата след ВТОРОТО ДС трябва да е повишената.
        v_mart = self.employee._get_version(date(2026, 3, 15))
        v_yuni = self.employee._get_version(date(2026, 6, 15))
        self.assertEqual(v_mart.wage, 2000.0, "повишението от 01.03 не е приложено")
        self.assertEqual(
            v_yuni.wage, 2000.0,
            "заплатата от 01.06 се е върнала на старата: по-късното ДС е "
            "копирало състоянието отпреди повишението")

    def _patch_today(self, day):
        """Кронът сравнява с `fields.Date.today()` — заместваме го за пробега."""
        from unittest.mock import patch
        from odoo import fields as odoo_fields
        return patch.object(
            odoo_fields.Date, "today", staticmethod(lambda *a, **k: day))
