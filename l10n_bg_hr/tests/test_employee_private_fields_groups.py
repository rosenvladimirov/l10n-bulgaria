# -*- coding: utf-8 -*-
"""Поле само на hr.employee трябва да е с група — иначе служител без права гърми.

Правилото е на ядрото (hr/models/hr_employee.py, бележката на класа HrEmployee):
поле, което го няма в hr.employee.public, трябва да е с
``groups="hr.group_hr_user"``. Без групата предварителното зареждане го
включва за потребител без права „Служители“ и ``_check_private_fields`` хвърля
„The fields … are not available for employee public profiles“.

Солид 55, 14.10.2026: „Моите задачи“ гърмеше за служителя заради 38 такива
полета в 9 модула на локализацията. Тестът е post_install и обхожда ВСИЧКИ
инсталирани модули — хваща и бъдещите нарушения, не само днешните.
"""
import os

from odoo.modules.module import get_module_path
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestEmployeePrivateFieldsGroups(TransactionCase):

    def _nash_modul(self, module):
        """Модул извън ядрото и Enterprise — нашите и на клиентите."""
        path = get_module_path(module, display_warning=False) or ''
        return bool(module) and not any(path.startswith(root) for root in self._core_roots())

    def _core_roots(self):
        # пътят на hr е в ядрото, на web_enterprise — в Enterprise (ако го има)
        roots = []
        for core in ('hr', 'web_enterprise'):
            path = get_module_path(core, display_warning=False)
            if path:
                roots.append(os.path.dirname(path) + os.sep)
        return roots

    def test_chastnite_poleta_sa_s_grupa(self):
        public = self.env['hr.employee.public']._fields
        bez_grupa = sorted(
            '%s (%s)' % (name, field._module)
            for name, field in self.env['hr.employee']._fields.items()
            # наследените от hr.version не се зареждат предварително, а
            # current_version_id ядрото изключва изрично (hr_employee.fetch)
            if name not in public and not field.groups and not field.inherited
            and name != 'current_version_id' and self._nash_modul(field._module)
        )
        self.assertFalse(
            bez_grupa,
            'Полета само на hr.employee без groups="hr.group_hr_user": %s' % ', '.join(bez_grupa),
        )

    def test_sluzhitel_bez_prava_chete_kolegata(self):
        """Служител без права „Служители“ вижда колегата си, както в „Моите задачи“."""
        colleague = self.env['hr.employee'].create({'name': 'Колега (тест)'})
        user = new_test_user(self.env, login='bg_employee_no_hr', groups='base.group_user')
        employee = colleague.with_user(user)
        # достъпът до поле предизвиква предварителното зареждане на всички
        # полета без група — точно там гърмеше
        self.assertEqual(employee.name, 'Колега (тест)')
        self.assertTrue(employee.display_name)
