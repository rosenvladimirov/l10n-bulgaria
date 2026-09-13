# -*- coding: utf-8 -*-
"""ДС, подписано след влизането в сила — допустимо, с предупреждение.

Пламена, 13.09.2026: „Визардът излага единствено датата на влизане в сила и
зашива датата на подписване на днес, а гардът иска подписване преди или на
датата на влизане в сила… Единственият начин да се запише е датата на
подписване да се излъже — а тя не е козметична: generate_etz_wizard.py я
подава като дата на промяната в уведомлението по чл. 62 КТ." Решение на Росен:
гардът става предупреждение, датата излиза на визарда.
"""
from datetime import date, timedelta

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'l10n_bg_ds_signed_after')
class TestAmendmentSignedAfterEffective(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Тест ДС с обратна дата', 'company_id': cls.env.company.id})
        cls.version = cls.employee.version_id
        # 🚨 `create` не задържа датата на версията — закотвя се отделно,
        # заедно с веригата сключване ≤ начало
        cls.version.write({'wage': 1500.0,
                           'l10n_bg_contract_date': date(2025, 1, 1),
                           'contract_date_start': date(2025, 1, 1)})
        cls.version.date_version = date(2025, 1, 1)
        cls.Amd = cls.env['l10n_bg.hr.version.amendment']

    def _amd(self, signed, effective):
        return self.Amd.create({
            'version_id': self.version.id, 'amendment_type': 'wage_change',
            'subject': 'Заплата', 'new_wage': 1600.0,
            'date_signed': signed, 'date_effective': effective})

    def test_signed_after_effective_is_accepted(self):
        """🚨 Същината: подписано днес с действие от първо число минава.

        Мутационната двойка: върни ограничението и този тест пада с
        ValidationError още при създаването.
        """
        dnes = date.today()
        parvo = dnes.replace(day=1) if dnes.day > 1 else dnes - timedelta(days=1)
        amd = self._amd(dnes, parvo)
        self.assertEqual(amd.date_signed, dnes,
                         'датата на подписване беше подменена')
        self.assertTrue(amd.l10n_bg_signed_after_effective,
                        'предупреждението не се вдигна')

    def test_signed_before_effective_raises_no_warning(self):
        """Контролата: обикновеното ДС не носи предупреждение."""
        dnes = date.today()
        amd = self._amd(dnes, dnes + timedelta(days=10))
        self.assertFalse(amd.l10n_bg_signed_after_effective)

    def test_the_wizard_passes_the_signature_date_through(self):
        """Визардът подава ВЪВЕДЕНАТА дата, не днешната."""
        vchera = date.today() - timedelta(days=1)
        wiz = self.env['l10n_bg.hr.version.amendment.wizard'].create({
            'employee_id': self.employee.id, 'version_id': self.version.id,
            'amendment_type': 'other', 'subject': 'Тест визард',
            'description': '<p>Уговорка</p>',
            'date_signed': vchera,
            'date_effective': date.today() - timedelta(days=5)})
        amd = self.Amd.browse(wiz.action_create_amendment()['res_id'])
        self.assertEqual(amd.date_signed, vchera,
                         'визардът пак зашива датата на подписване на днес')
