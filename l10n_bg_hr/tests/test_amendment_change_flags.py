# -*- coding: utf-8 -*-
"""DEF-210 т. 1–3 и 7 — отметки „какво се променя“, основание, код по т. 12.

Пламена, 15.10.2026 (ТГ 172092): видът беше едно поле и съветникът показваше
заплата и длъжност само поотделно, макар прилагането да поема всички попълнени
промени. Правното основание беше свободен текст; ЕТЗ подаваше основанието на
договора (001) вместо на изменението (018–021).
"""
import importlib.util
import os
from datetime import date

from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_path
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAmendmentChangeFlags(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Отметки ДС",
            "company_id": cls.env.company.id,
            "date_version": "2026-01-01",
        })
        cls.version = cls.employee.version_id
        cls.version.write({
            "wage": 1500.0,
            "contract_date_start": date(2026, 1, 1),
            "l10n_bg_contract_date": date(2026, 1, 1),
        })
        cls.job = cls.env["hr.job"].create({"name": "Тест Нова Длъжност"})

    def _ds(self, **vals):
        return self.env["l10n_bg.hr.version.amendment"].create(dict({
            "version_id": self.version.id,
            "date_signed": date(2026, 8, 1),
            "date_effective": date(2026, 9, 1),
            "subject": "Тест",
        }, **vals))

    def test_a_legacy_type_gets_its_flag(self):
        """Заварен код, импорт, RPC: видът без отметки дава своята отметка."""
        amd = self._ds(amendment_type="wage_change", new_wage=1700.0)
        self.assertTrue(amd.l10n_bg_chg_wage)
        self.assertEqual(amd.l10n_bg_etz_change_code, "019")

    def test_two_changes_in_one_agreement(self):
        """🚨 Същината: заплата и длъжност в едно ДС — вид „Друго“, код 021."""
        amd = self._ds(amendment_type="additional_duties",
                       l10n_bg_chg_wage=True, l10n_bg_chg_position=True,
                       new_wage=1800.0, new_job_id=self.job.id,
                       description="Повишение")
        self.assertEqual(amd.amendment_type, "other")
        self.assertEqual(amd.l10n_bg_etz_change_code, "021")
        self.assertFalse(
            amd._l10n_bg_is_textual(),
            "ДС с отметки мина за текстово — промените няма да се приложат")
        amd.action_submit_for_approval()
        amd.action_approve()
        amd.action_activate()
        nova = amd.applied_version_id
        self.assertNotEqual(nova, self.version)
        self.assertAlmostEqual(nova.wage, 1800.0, places=2)
        self.assertEqual(nova.job_id, self.job)

    def test_codes_by_change(self):
        cases = [
            ({"l10n_bg_chg_wage": True, "new_wage": 1600.0}, "019"),
            ({"l10n_bg_chg_working_time": True}, "020"),
            ({"l10n_bg_chg_leave": True, "new_leave_days": 25}, "021"),
            ({"l10n_bg_chg_wage": True, "l10n_bg_chg_workplace": True,
              "new_wage": 1600.0}, "021"),
        ]
        for vals, code in cases:
            amd = self._ds(amendment_type="other", **vals)
            self.assertEqual(amd.l10n_bg_etz_change_code, code, vals)
            self.assertTrue(amd.l10n_bg_etz_registrable)

    def test_additional_duties_only_is_not_registrable(self):
        """Т. 7: само допълнителни задължения — няма какво да се впише."""
        amd = self._ds(amendment_type="additional_duties",
                       description="Допълнителни задължения")
        self.assertFalse(amd.l10n_bg_etz_change_code)
        self.assertFalse(amd.l10n_bg_etz_registrable)

    def test_posting_is_018_under_art_121a(self):
        amd = self._ds(amendment_type="temporary_assignment",
                       is_temporary=True, is_temporary_assignment=True,
                       date_end=date(2026, 10, 31))
        self.assertEqual(amd.l10n_bg_etz_change_code, "018")
        self.assertEqual(amd.l10n_bg_legal_basis, "art121a")

    def test_order_118_3_only_for_a_wage_increase(self):
        self._ds(amendment_type="wage_change", new_wage=1700.0,
                 old_wage=1500.0, l10n_bg_legal_basis="art118_3")
        with self.assertRaises(ValidationError):
            self._ds(amendment_type="wage_change", new_wage=1400.0,
                     old_wage=1500.0, l10n_bg_legal_basis="art118_3")
        with self.assertRaises(ValidationError):
            self._ds(amendment_type="other", l10n_bg_chg_wage=True,
                     l10n_bg_chg_position=True, new_wage=1700.0,
                     old_wage=1500.0, new_job_id=self.job.id,
                     l10n_bg_legal_basis="art118_3")

    def test_order_138a_only_for_working_time(self):
        with self.assertRaises(ValidationError):
            self._ds(amendment_type="wage_change", new_wage=1700.0,
                     l10n_bg_legal_basis="art138a")

    def test_migration_flags_existing_amendments(self):
        """Заварените ДС получават отметки по вида и по попълнените стойности."""
        po_vid = self._ds(amendment_type="leave_change", new_leave_days=26)
        drugo = self._ds(amendment_type="other", l10n_bg_chg_wage=True,
                         new_wage=1650.0)
        vneseno = self._ds(amendment_type="other")
        komandirovka = self._ds(amendment_type="temporary_assignment",
                                is_temporary=True, is_temporary_assignment=True,
                                date_end=date(2026, 10, 31))
        self.env.flush_all()
        # както я ражда ъпгрейдът: колоната е попълнена с подразбиращото се
        self.env.cr.execute(
            "UPDATE l10n_bg_hr_version_amendment SET l10n_bg_legal_basis = "
            "'art119' WHERE id = %s", (komandirovka.id,))
        self.env.cr.execute(
            "UPDATE l10n_bg_hr_version_amendment SET l10n_bg_chg_wage = FALSE, "
            "l10n_bg_chg_leave = FALSE, amendment_type = %s WHERE id = %s",
            ("other", drugo.id))
        self.env.cr.execute(
            "UPDATE l10n_bg_hr_version_amendment SET l10n_bg_chg_leave = FALSE "
            "WHERE id = %s", (po_vid.id,))
        path = os.path.join(get_module_path("l10n_bg_hr"),
                            "migrations", "19.0.2.9.18", "post-migrate.py")
        spec = importlib.util.spec_from_file_location("l10n_bg_hr_mig_29_18", path)
        mig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig)
        mig.migrate(self.env.cr, "19.0.2.9.17")
        (po_vid | drugo | vneseno).invalidate_recordset()
        self.assertTrue(po_vid.l10n_bg_chg_leave)
        self.assertTrue(drugo.l10n_bg_chg_wage)
        self.assertFalse(vneseno._l10n_bg_flags())
        self.assertFalse(vneseno.l10n_bg_etz_registrable)
        komandirovka.invalidate_recordset()
        self.assertEqual(komandirovka.l10n_bg_legal_basis, "art121a",
                         "командироването остана по чл. 119")
