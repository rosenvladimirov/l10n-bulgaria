# -*- coding: utf-8 -*-
"""Версия на служител се отваря в собствената форма, не в шаблонната на ядрото.

ADR l10n-bg-contract-amendments/0005 (14.09.2026): шаблонната „Contract Template“
иска „Template Name“ задължително — за версия на служител това е чуждо поле.
Шаблонът (версия без служител) остава в шаблонната форма.
"""
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestVersionFormView(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view = cls.env.ref('l10n_bg_hr.hr_version_employee_record_form_view')
        cls.employee = cls.env['hr.employee'].create({'name': 'Version Form 1409'})
        cls.version = cls.employee.version_id

    def test_history_row_opens_our_form(self):
        act = self.version.action_open_version()
        self.assertEqual((act['res_model'], act['res_id']), ('hr.version', self.version.id))
        self.assertEqual(act['views'], [(self.view.id, 'form')],
                         'ред от „History“ не отваря собствената форма на версията')

    def test_debug_view_button_opens_our_form(self):
        act = self.version.action_open_version_form_view()
        self.assertEqual(act['views'][0][0], self.view.id,
                         'бутонът „View“ още отваря шаблонната форма')

    def test_a_template_keeps_the_template_form(self):
        shablon = self.env['hr.version'].create({'name': 'Template 1409'})
        self.assertFalse(shablon.employee_id)
        self.assertEqual(shablon.action_open_version()['views'], [(False, 'form')])
        self.assertEqual(shablon.action_open_version_form_view()['views'][0][0],
                         self.env.ref('hr.hr_contract_template_form_view').id)

    def test_the_template_is_still_the_default_form(self):
        # Шаблонната форма остава по подразбиране — нашата е с по-нисък приоритет.
        self.assertEqual(self.env['ir.ui.view'].default_view('hr.version', 'form'),
                         self.env.ref('hr.hr_contract_template_form_view').id)

    def test_template_name_is_hidden_and_the_bg_extensions_are_inherited(self):
        arch = self.view._get_combined_arch()
        name = arch.xpath("//field[@name='name']")
        self.assertTrue(name, 'полето name е махнато — чужди разширения биха увиснали')
        self.assertEqual((name[0].get('required'), name[0].get('invisible')), ('0', '1'),
                         '„Template Name“ още е видимо или задължително')
        self.assertTrue(arch.xpath("//div[@name='title']//field[@name='employee_id']"),
                        'служителят липсва от заглавието')
        self.assertTrue(arch.xpath("//field[@name='l10n_bg_contract_number']"),
                        'номерът на трудовия договор липсва от формата')
        # Основният наследник носи и разширенията на шаблонната форма (НКПД/КИД на l10n_bg_hr).
        self.assertTrue(arch.xpath("//field[@name='l10n_bg_workplace_code']"),
                        'разширенията на шаблонната форма не стигат до новата')
