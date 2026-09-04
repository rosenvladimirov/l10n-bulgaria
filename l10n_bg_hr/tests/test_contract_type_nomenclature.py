# -*- coding: utf-8 -*-
"""DEF-173а/б — срочната линия беше доставена инертна.

Механизмът е верен: и двата крона вършат точно каквото трябва. Но на никоя база
не може да се задейства, защото номенклатурата се доставяше НЕПОПЪЛНЕНА.

Полето, което класифицира двайсет и едните български вида договори, е дефинирано
с подразбиращо се ``indefinite`` и в нито един данен файл не се среща. Домейнът
и на двата крона изисква режим, различен от ``indefinite`` — тъй че на чиста
инсталация те не намират нищо, никога.

Мерено от Пламена: попълването на шестте еднозначни кода веднага даде 168 версии
със срочен режим на тестовата база (167 на код 003, една на 002); на CLEAN-1606
версиите на код 003 са 145.
"""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestContractTypeNomenclature(TransactionCase):

    # ⚖️ Чл. 68, ал. 1 КТ — съответствието е нормативно, не клиентско.
    EDNOZNACHNI = {
        "l10n_bg_001": "indefinite",     # чл. 67, ал. 1, т. 1
        "l10n_bg_002": "fixed_term",     # чл. 68, ал. 1, т. 1
        "l10n_bg_003": "specific_work",  # т. 2
        "l10n_bg_004": "replacement",    # т. 3
        "l10n_bg_005": "fixed_term",     # т. 4
        "l10n_bg_006": "fixed_term",     # т. 5
    }

    def test_the_unambiguous_codes_are_classified(self):
        """🚨 Същината: доставената номенклатура вече носи режима."""
        for xmlid, ochakvan in self.EDNOZNACHNI.items():
            vid = self.env.ref("l10n_bg_hr.%s" % xmlid)
            self.assertEqual(
                vid.l10n_bg_contract_duration_type, ochakvan,
                "код %s стои на подразбиращото се — крънът няма да го намери "
                "никога" % vid.code)

    def test_the_crons_can_now_find_something(self):
        """Домейнът на крона среща поне един вид, различен от безсрочния."""
        srochni = self.env["hr.contract.type"].search([
            ("l10n_bg_contract_duration_type", "!=", "indefinite"),
            ("country_id.code", "=", "BG"),
        ])
        self.assertTrue(
            srochni,
            "нула срочни вида — цялата срочна линия е недостижима")

    def test_the_ambiguous_codes_are_left_alone(self):
        """🔲 Петте двусмислени НЕ се пипат — чакат решение.

        Мутация: попълни ли ги някой наслуки, тестът пада и въпросът излиза
        наяве, вместо да се разсее в данните.
        """
        for xmlid in ("l10n_bg_007", "l10n_bg_014", "l10n_bg_015",
                      "l10n_bg_016", "l10n_bg_017"):
            vid = self.env.ref("l10n_bg_hr.%s" % xmlid)
            self.assertEqual(
                vid.l10n_bg_contract_duration_type, "indefinite",
                "код %s е класифициран, а решението за него не е взето" %
                vid.code)

    def test_the_duration_is_reachable_from_the_list(self):
        """DEF-172е — полето трябва да го има там, където се редактира.

        Ядреното действие е само списък, а списъкът е редактируем на място;
        формата не се отваря. Поле само във формата е недостижимо.
        """
        spisak = self.env.ref("hr.hr_contract_type_view_tree")
        arch = self.env["hr.contract.type"].get_view(
            spisak.id, "list")["arch"]
        self.assertIn(
            "l10n_bg_contract_duration_type", arch,
            "режимът не е в списъка — номенклатурата не може да се попълни от "
            "екрана")


@tagged("post_install", "-at_install")
class TestFixedTermEndRequired(TransactionCase):
    """DEF-173б — срочен договор без срок е невидим за крона."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Тест Срок Задължителен",
            "company_id": cls.env.company.id,
        })
        cls.vid_srochen = cls.env.ref("l10n_bg_hr.l10n_bg_002")
        cls.vid_rabota = cls.env.ref("l10n_bg_hr.l10n_bg_003")

    def test_fixed_term_without_an_end_is_refused(self):
        """🚨 Същината."""
        with self.assertRaises(ValidationError):
            self.employee.version_id.write({
                "contract_type_id": self.vid_srochen.id,
                "l10n_bg_fixed_term_end": False,
            })

    def test_fixed_term_with_an_end_passes(self):
        self.employee.version_id.write({
            "contract_type_id": self.vid_srochen.id,
            "l10n_bg_fixed_term_end": date(2027, 6, 30),
        })
        self.assertEqual(
            self.employee.version_id.l10n_bg_contract_duration_type,
            "fixed_term")

    def test_specific_work_does_not_demand_a_date(self):
        """🚨 Регресия: „до завършване на определена работа" няма дата.

        Чл. 68, ал. 1, т. 2 свършва със самата работа. Изискването на дата там
        би принудило ТРЗ да измисля число.
        """
        self.employee.version_id.write({
            "contract_type_id": self.vid_rabota.id,
            "l10n_bg_fixed_term_end": False,
        })
        self.assertEqual(
            self.employee.version_id.l10n_bg_contract_duration_type,
            "specific_work")

    def test_indefinite_does_not_demand_a_date(self):
        """Регресия: безсрочният също няма срок."""
        self.employee.version_id.write({
            "contract_type_id": self.env.ref("l10n_bg_hr.l10n_bg_001").id,
            "l10n_bg_fixed_term_end": False,
        })
        self.assertFalse(self.employee.version_id.l10n_bg_fixed_term_end)
