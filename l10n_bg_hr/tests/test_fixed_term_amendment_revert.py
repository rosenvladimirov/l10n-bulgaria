# -*- coding: utf-8 -*-
"""DEF-104Б А.2 — изтичането на СРОЧНО ДС не връщаше нищо.

Кронът търси по ``is_temporary`` (срочност), а после питаше
``is_temporary_assignment`` (ТИП — временно преместване). Срочно ДС по
чл. 119, ал. 1 КТ има срочност, но няма тип; кронът го обявяваше за изтекло и
не връщаше нищо. Отделно клон за заплатата изобщо нямаше, а ``old_wage``
стоеше неизползвано.

Носител на Пламена: служител 902, ДС 342, тип „Друго", вдигнат флаг „Срочно",
заплата 613,56 → 1000,00 и длъжност 214 → 211. След крона: състояние
„Изтекло", нова версия няма, заплатата остава 1000,00.
"""
from datetime import date
from unittest.mock import patch

from odoo import fields as odoo_fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFixedTermAmendmentRevert(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_staro = cls.env["hr.job"].create({"name": "Специалист DEF104"})
        cls.job_novo = cls.env["hr.job"].create({"name": "Ръководител DEF104"})
        # 🚨 `date_version` е ЗАДЪЛЖИТЕЛНО тук. Без него първата версия пада на
        # ДНЕС, а тестът работи с дати през 2026 г.: оригиналната версия
        # застава СЛЕД върнатата и всяко четене „към 10.09" попада на нея.
        #
        # Заради това `test_..._reverts_the_job` минаваше ПО СЛУЧАЙНОСТ —
        # оригиналът носи старата длъжност, която тестът очаква, тъй че зелено
        # се получаваше без връщането изобщо да е работило.
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Срочно ДС",
            "company_id": cls.env.company.id,
            "date_version": "2026-01-01",
        })
        cls.version = cls.employee.version_id
        cls.version.write({"wage": 613.56, "job_id": cls.job_staro.id})

    def _srochno_ds(self, **vals):
        """Срочно ДС по чл. 119, ал. 1 — срочност БЕЗ тип „преместване"."""
        amd = self.env["l10n_bg.hr.version.amendment"].create(dict({
            "version_id": self.version.id,
            "amendment_type": "other",
            "date_signed": date(2026, 7, 15),
            "date_effective": date(2026, 8, 1),
            "date_end": date(2026, 9, 2),
            "is_temporary": True,
            "is_temporary_assignment": False,
            "subject": "Срочно изменение по чл. 119, ал. 1",
            "new_wage": 1000.0,
            "new_job_id": self.job_novo.id,
        }, **vals))
        amd.action_submit_for_approval()
        amd.action_approve()
        amd.action_activate()
        return amd

    def _izteche(self, na=date(2026, 9, 10)):
        with patch.object(odoo_fields.Date, "today",
                          staticmethod(lambda *a, **k: na)):
            self.env["l10n_bg.hr.version.amendment"] \
                .cron_expire_temporary_amendments()

    def test_fixed_term_amendment_reverts_the_job(self):
        """🚨 Гардът беше на типа, а срочното ДС няма тип."""
        amd = self._srochno_ds()
        self._izteche()
        self.assertEqual(amd.state, "expired")
        sled = self.employee._get_version(date(2026, 9, 10))
        self.assertEqual(
            sled.job_id, self.job_staro,
            "срочното ДС изтече и не върна длъжността — гардът пита за типа "
            "вместо за срочността")

    def test_fixed_term_amendment_reverts_the_wage(self):
        """🚨 Клон за заплатата нямаше изобщо, а old_wage стоеше неизползвано.

        ⚖️ Чл. 267, ал. 3 КТ: при друга работа поради производствена
        необходимост се плаща възнаграждението за изпълняваната работа, но не
        по-малко от брутното за основната. Последица от закона, обвързана с
        периода — свърши ли периодът, отпада и основанието.
        """
        self._srochno_ds()
        self._izteche()
        sled = self.employee._get_version(date(2026, 9, 10))
        self.assertAlmostEqual(
            sled.wage, 613.56, places=2,
            msg="заплатата остана вдигната след изтичането на срочното ДС")

    def test_the_temporary_period_keeps_its_own_terms(self):
        """Периодът на изменението остава описан, не се изтрива."""
        self._srochno_ds()
        self._izteche()
        v_avgust = self.employee._get_version(date(2026, 8, 15))
        self.assertEqual(v_avgust.job_id, self.job_novo)
        self.assertAlmostEqual(v_avgust.wage, 1000.0, places=2)

    def test_a_later_raise_is_not_silently_cut(self):
        """🚨 Гардът: по-късно вдигане на заплатата не се прегазва.

        Връщането е валидно само докато ефектът на ТОВА ДС стои. Смени ли я
        друго ДС, връщането към old_wage би било мълчаливо намаление на
        възнаграждение, за което има подписан документ.
        """
        amd = self._srochno_ds()
        # Второ ДС вдига заплатата ВЪТРЕ в периода на първото.
        po_kasna = self.employee.create_version({
            "date_version": date(2026, 8, 20),
            "wage": 1400.0,
        })
        # Междинни твърдения: без тях провалът казва само „накрая е грешно",
        # а не КЪДЕ се къса веригата.
        self.assertAlmostEqual(
            po_kasna.wage, 1400.0, places=2,
            msg="по-късната версия не носи новата заплата")
        self.assertAlmostEqual(
            self.employee._get_version(amd.date_end).wage, 1400.0, places=2,
            msg="към края на ДС-то в сила е друга заплата, не по-късната")
        self.assertAlmostEqual(
            amd.new_wage, 1000.0, places=2,
            msg="ДС-то не помни какво е поставило")
        # 🔑 Питаме гарда ПРЯКО. Инак провалът казва само „накрая е грешно",
        # а не дали гардът е решил вярно и после нещо друго е прегазило.
        self.assertFalse(
            amd._l10n_bg_wage_still_ours(),
            "гардът смята, че заплатата още е неговата, а тя е сменена")
        self._izteche()
        sled = self.employee._get_version(date(2026, 9, 10))
        self.assertAlmostEqual(
            sled.wage, 1400.0, places=2,
            msg="изтичането преби по-късно договорено възнаграждение")
        self.assertTrue(
            any("Wage not restored" in (m.body or "")
                for m in amd.message_ids),
            "отказът да се върне заплатата не е обяснен в чатъра")

    def test_amendment_without_wage_change_does_not_touch_it(self):
        """ДС, което не е пипало заплатата, не я връща."""
        self._srochno_ds(new_wage=0.0)
        self._izteche()
        sled = self.employee._get_version(date(2026, 9, 10))
        self.assertAlmostEqual(sled.wage, 613.56, places=2)
