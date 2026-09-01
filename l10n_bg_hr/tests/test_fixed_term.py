# -*- coding: utf-8 -*-
"""Срокът на срочния договор не е прекратяването му.

⚖️ Ядреният `contract_date_end` е ПРЕКРАТЯВАНЕТО. Срочният договор има
УГОВОРЕН СРОК, който може да изтече, без някой да прекрати — и тогава
чл. 69, ал. 1 КТ действа сам: продължи ли работникът пет или повече работни
дни след срока без писмено възражение, договорът става БЕЗСРОЧЕН.

Затова има два крона: единият предупреждава ПРЕДИ срока (заради уведомлението
до НАП по чл. 62, ал. 5 КТ), другият е последната мрежа СЛЕД петте дни.

Мутационни проверки (01.09.2026):
· махни изчакването `dnes <= deadline` → `test_within_the_five_days_nothing_moves` пада;
· смени `timedelta(days=1)` на нула → `test_new_version_starts_the_day_after` пада;
· махни обхвата по `l10n_bg_contract_duration_type` →
  `test_indefinite_contract_is_never_touched` пада.
"""
from datetime import date, timedelta

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFixedTerm(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vid_srochen = cls.env["hr.contract.type"].create({
            "name": "Тест срочен", "code": "TSR",
            "l10n_bg_contract_duration_type": "fixed_term",
        })
        cls.vid_bezsrochen = cls.env["hr.contract.type"].create({
            "name": "Тест безсрочен", "code": "TBS",
            "l10n_bg_contract_duration_type": "indefinite",
        })

    def _version(self, srok, sled=None, vid=None):
        emp = self.env["hr.employee"].create({"name": "Тест срок"})
        v = emp.version_id
        v.write({
            "wage": 1000.0,
            "contract_type_id": (vid or self.vid_srochen).id,
            "l10n_bg_fixed_term_end": srok,
            "l10n_bg_after_term_contract_type_id": sled and sled.id or False,
        })
        return v

    # ------------------------------------------------------------------

    def test_within_the_five_days_nothing_moves(self):
        """Прозорецът на чл. 69 още тече — човекът има думата, не кронът."""
        v = self._version(date.today() - timedelta(days=1))
        self.env["hr.version"].cron_l10n_bg_close_overdue_fixed_terms()
        self.assertFalse(
            v.contract_date_end,
            "кронът прекрати договор, докато петте работни дни още текат — "
            "отнема на ТРЗ-то законния прозорец да реагира")

    def test_empty_ground_terminates_on_the_term_date(self):
        """Празно „договор след срока" значи прекратяване НА датата на срока."""
        srok = date.today() - timedelta(days=30)
        v = self._version(srok)
        self.env["hr.version"].cron_l10n_bg_close_overdue_fixed_terms()
        self.assertEqual(
            v.contract_date_end, srok,
            "прекратяването не е на датата на срока")

    def test_new_version_starts_the_day_after(self):
        """Попълненото основание ражда версия от срок + 1, не от самия срок.

        Две версии върху ЕДИН ден дават припокриващи се подпериоди в
        т. 14/15 на Д1 — точно записът, който НАП отхвърля.
        """
        srok = date.today() - timedelta(days=30)
        v = self._version(srok, sled=self.vid_bezsrochen)
        self.env["hr.version"].cron_l10n_bg_close_overdue_fixed_terms()
        self.assertEqual(v.contract_date_end, srok)
        novi = v.employee_id.version_ids.filtered(
            lambda x: x.id != v.id
            and x.contract_type_id == self.vid_bezsrochen)
        self.assertTrue(novi, "не е родена нова версия с новото основание")
        self.assertEqual(
            novi[0].date_version, srok + timedelta(days=1),
            "новата версия започва в деня на срока — застъпва стария договор")
        self.assertFalse(
            novi[0].l10n_bg_fixed_term_end,
            "новата версия наследи срок, макар да е по друго основание")

    def test_indefinite_contract_is_never_touched(self):
        """Безсрочният няма срок за изтичане — кронът не бива да го пипа."""
        v = self._version(date.today() - timedelta(days=30),
                          vid=self.vid_bezsrochen)
        self.env["hr.version"].cron_l10n_bg_close_overdue_fixed_terms()
        self.assertFalse(
            v.contract_date_end,
            "кронът прекрати БЕЗСРОЧЕН договор заради дата в поле, което за "
            "него няма смисъл")

    def test_terminated_contract_is_left_alone(self):
        """Прекратеното е прекратено — няма какво да се довършва."""
        srok = date.today() - timedelta(days=30)
        rachno = srok - timedelta(days=5)
        v = self._version(srok)
        v.contract_date_end = rachno
        self.env["hr.version"].cron_l10n_bg_close_overdue_fixed_terms()
        self.assertEqual(
            v.contract_date_end, rachno,
            "кронът презаписа ръчно въведена дата на прекратяване")

    def test_notice_goes_out_before_the_term(self):
        """Предупреждението е нормалният път — мрежата е изключението."""
        v = self._version(date.today() + timedelta(days=3))
        predi = len(v.message_ids)
        self.env["hr.version"].cron_l10n_bg_notify_expiring_fixed_terms()
        self.assertGreater(
            len(v.message_ids), predi,
            "срокът изтича след три дни, а никой не е предупреден — "
            "уведомлението до НАП няма как да бъде подадено навреме")
