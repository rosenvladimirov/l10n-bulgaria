# -*- coding: utf-8 -*-
"""Заявка Полигруп, лист „28.08" (HR_ERP_1.xlsx) — кадровите точки.

Три неща, които трябва да са верни на ВСЯКА българска база, не само на
Полигруп: образователната стълбица по ЗПУО/ЗВО, държавата на гражданството
по подразбиране и уведомлението три месеца преди срока на документите.

🔑 Уведомлението се проверява и за ДУБЛИКАТ: кронът върви всеки ден, а една
дейност на документ е точно това, което ТРЗ ще търпи. Втори пробег, който
ражда втора дейност, е шум, който след седмица никой не чете.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'l10n_bg_hr_documents')
class TestSheet2808Documents(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Тест Документи',
            'company_id': cls.env.company.id,
        })
        cls.version = cls.employee.version_id
        cls.Activity = cls.env['mail.activity']
        cls.model_emp = cls.env['ir.model']._get_id('hr.employee')

    def _deinosti(self):
        return self.Activity.search([
            ('res_model_id', '=', self.model_emp),
            ('res_id', '=', self.employee.id),
        ])

    # --- образование --------------------------------------------------------

    def test_education_ladder_is_bulgarian_and_keeps_core_keys(self):
        """Основно и средно СА в списъка; ядрените ключове не са изгубени."""
        klyuchove = [k for k, _v in
                     self.env['hr.employee']._get_certificate_selection()]
        for k in ('l10n_bg_basic', 'l10n_bg_secondary',
                  'l10n_bg_vocational_bachelor', 'bachelor', 'master',
                  'doctor', 'l10n_bg_doctor_of_science'):
            self.assertIn(k, klyuchove)
        # заварените стойности остават валидни — по тях има данни
        for k in ('graduate', 'other'):
            self.assertIn(k, klyuchove)
        # редът е възходящ, не азбучен
        red = [klyuchove.index(k) for k in (
            'l10n_bg_basic', 'l10n_bg_secondary', 'bachelor', 'master',
            'doctor', 'l10n_bg_doctor_of_science')]
        self.assertEqual(red, sorted(red))

    def test_basic_education_is_writable(self):
        self.employee.certificate = 'l10n_bg_basic'
        self.assertEqual(self.employee.certificate, 'l10n_bg_basic')

    # --- гражданство --------------------------------------------------------

    def test_default_citizenship_is_the_company_country(self):
        self.assertEqual(self.version.country_id,
                         self.env.company.country_id)

    # --- уведомление за документите ------------------------------------------

    def test_expiring_id_card_raises_exactly_one_activity(self):
        dnes = fields.Date.today()
        self.version.write({
            'l10n_bg_id_card_number': '123456789',
            'l10n_bg_id_card_expiry': dnes + timedelta(days=30),
        })
        self.assertFalse(self._deinosti())
        broi = self.env['hr.version'].cron_l10n_bg_notify_expiring_documents()
        self.assertGreaterEqual(broi, 1)
        moite = self._deinosti()
        self.assertEqual(len(moite), 1)
        self.assertIn('ID card', moite.summary)
        self.assertEqual(moite.date_deadline, dnes + timedelta(days=30))
        # втори пробег — НЕ ражда втора дейност за същия документ и срок
        self.env['hr.version'].cron_l10n_bg_notify_expiring_documents()
        self.assertEqual(len(self._deinosti()), 1)

    def test_renewed_document_is_a_new_notification(self):
        """Нов срок = ново резюме = нова дейност; старата не го блокира."""
        dnes = fields.Date.today()
        self.version.write({
            'l10n_bg_id_card_number': '1',
            'l10n_bg_id_card_expiry': dnes + timedelta(days=30),
        })
        self.env['hr.version'].cron_l10n_bg_notify_expiring_documents()
        self.version.l10n_bg_id_card_expiry = dnes + timedelta(days=45)
        self.env['hr.version'].cron_l10n_bg_notify_expiring_documents()
        self.assertEqual(len(self._deinosti()), 2)

    def test_far_and_past_expiries_are_silent(self):
        dnes = fields.Date.today()
        self.version.write({
            'l10n_bg_id_card_number': '1',
            'l10n_bg_id_card_expiry': dnes + timedelta(days=200),
            'l10n_bg_protection_status': 'temporary',
            'l10n_bg_protection_expiry': dnes - timedelta(days=1),
        })
        self.env['hr.version'].cron_l10n_bg_notify_expiring_documents()
        self.assertFalse(self._deinosti())

    def test_core_expiries_ride_the_same_notification(self):
        """Паспортът (на версията) и разрешението за работа (на служителя)
        минават през същия крон — не втори механизъм."""
        dnes = fields.Date.today()
        self.version.passport_expiration_date = dnes + timedelta(days=10)
        self.employee.work_permit_expiration_date = dnes + timedelta(days=60)
        self.env['hr.version'].cron_l10n_bg_notify_expiring_documents()
        rezyumeta = self._deinosti().mapped('summary')
        self.assertEqual(len(rezyumeta), 2)
        self.assertTrue(any('Passport' in r for r in rezyumeta))
        self.assertTrue(any('Work permit' in r for r in rezyumeta))

    def test_archived_employee_wakes_nobody(self):
        dnes = fields.Date.today()
        self.version.write({
            'l10n_bg_id_card_number': '1',
            'l10n_bg_id_card_expiry': dnes + timedelta(days=30),
        })
        self.employee.active = False
        self.env['hr.version'].cron_l10n_bg_notify_expiring_documents()
        self.assertFalse(self._deinosti())
