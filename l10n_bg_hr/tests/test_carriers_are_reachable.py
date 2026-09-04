# -*- coding: utf-8 -*-
"""DEF-172 — кодът поддържа повече, отколкото екранът позволява да се въведе.

Осемте точки на Пламена са една фигура: полето или екранът съществува в кода,
работи, и няма път до него от интерфейса. Прецедентът е DEF-107 — „new_job_id не
съществува в нито един изглед" — поправен по същата формулировка.

Проверката е структурна: чете се архитектурата на изгледа, не се симулира клик.
Така тестът пада при всяко бъдещо пренареждане, което пак скрие носителя.
"""
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCarriersAreReachable(TransactionCase):

    def _arch(self, xmlid, view_type="form", model="l10n_bg.hr.version.amendment"):
        izgled = self.env.ref(xmlid)
        return self.env[model].get_view(izgled.id, view_type)["arch"]

    def test_the_work_location_record_is_offered_on_the_form(self):
        """🚨 (а) Носителят е ЗАПИСЪТ, а екранът предлагаше само текст.

        ``_apply_version_changes`` при попълнен само текст не пише нищо на
        версията и оставя предупреждение в лога. Тоест временно преместване по
        МЯСТО не можеше да промени нищо, а връщането при изтичане се строи
        именно от ``old_work_location_id``.
        """
        arch = self._arch("l10n_bg_hr.view_l10n_bg_hr_contract_amendment_form")
        self.assertIn("new_work_location_id", arch)
        self.assertIn("old_work_location_id", arch)

    def test_the_work_location_record_is_offered_in_the_wizard(self):
        """Същото и по пътя, по който ДС-та се създават най-често."""
        arch = self._arch(
            "l10n_bg_hr.view_hr_version_amendment_wizard_form",
            model="l10n_bg.hr.version.amendment.wizard")
        self.assertIn("new_work_location_id", arch)

    def test_the_end_date_shows_for_every_type_that_accepts_it(self):
        """🚨 (в) Формата криеше полето по флага, визардът го приема по ТИПА.

        Пропусне ли се при създаването, не можеше да се добави после — оставаше
        само отказ и ново ДС по същия подписан документ.
        """
        arch = self._arch("l10n_bg_hr.view_l10n_bg_hr_contract_amendment_form")
        self.assertIn("contract_extension", arch,
                      "„Удължаване на срока“ още не показва крайната дата")

    def test_the_amendments_menu_does_not_bury_contract_templates(self):
        """🚨 (з) Един ред, който чупеше две неща наведнъж.

        Родителят НОСИ действие (Шаблони за договори). Odoo 19 рендира меню с
        деца като заглавие на секция, тъй че шаблоните станаха недостижими — а
        клиентът ги иска.
        """
        menu = self.env.ref("l10n_bg_hr.menu_l10n_bg_hr_contract_amendment")
        shabloni = self.env.ref("hr.menu_hr_employee_contract_templates")
        self.assertNotEqual(
            menu.parent_id, shabloni,
            "споразуменията още висят под „Шаблони за договори“ и го правят "
            "заглавие на секция")
        self.assertEqual(
            menu.parent_id, self.env.ref("hr.menu_config_recruitment"),
            "менюто не е сестра на Работни позиции, Шаблони и Видове заетост")
        self.assertFalse(
            shabloni.child_id,
            "„Шаблони за договори“ пак има деца — действието му е недостижимо")
