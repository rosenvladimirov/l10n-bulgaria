# -*- coding: utf-8 -*-
"""Историята на решенията на ТЕЛК — резолвърът по дата, гардовете и бутонът.

Моделът е ПРЕНЕСЕН от `-v20` (`l10n_bg_version`); тестовете тук пазят
поведението му в каноничния слой и покриват онова, което там нямаше: връзката
към служителя и разликата „няма решение" срещу „решението е изтекло".

Бутонът, който пренася решението към версията, живее в `l10n_bg_hr_payroll`
(там е полето за процента) и се тества там — `test_telk_button_applies`.

Същината не е „кой е процентът", а „кой е процентът КЪМ КОЯ ДАТА". Тест, който
пита само за днес, минава зелено и върху старото поведение, при което новото
решение презаписваше старото.
"""
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'l10n_bg_telk')
class TestTelkDecisionHistory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Decision = cls.env['l10n_bg.telk.decision']
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Тест ТЕЛК История',
            'company_id': cls.env.company.id,
        })
        cls.drug = cls.env['hr.employee'].create({
            'name': 'Втори Служител',
            'company_id': cls.env.company.id,
        })

    def _reshenie(self, ot, do, procent, nomer, employee=None):
        return self.Decision.create({
            'employee_id': (employee or self.employee).id,
            'number': nomer,
            'issuing_body': 'ТЕЛК Тест',
            'date_from': ot,
            'date_to': do,
            'percent': procent,
        })

    # ── резолвърът по дата: същината ──────────────────────────────────────

    def test_the_answer_depends_on_the_date(self):
        """Две решения, две дати, два различни отговора."""
        self._reshenie('2024-01-01', '2025-12-31', 50, 'A/2024')
        self._reshenie('2026-01-01', None, 71, 'B/2026')
        staro = self.Decision.decision_at(self.employee, '2025-06-30')
        novo = self.Decision.decision_at(self.employee, '2026-06-30')
        self.assertEqual(staro.number, 'A/2024')
        self.assertEqual(staro.percent, 50)
        self.assertEqual(novo.number, 'B/2026')
        self.assertEqual(novo.percent, 71,
                         "новото решение не бива да презаписва старото")

    def test_a_date_before_any_decision_gives_nothing(self):
        self._reshenie('2026-01-01', None, 71, 'B/2026')
        self.assertFalse(
            self.Decision.decision_at(self.employee, '2025-06-30'),
            "преди първото решение няма процент")

    def test_a_gap_after_expiry_gives_nothing(self):
        """Изтекло решение без последващо НЕ се проточва."""
        self._reshenie('2024-01-01', '2024-12-31', 50, 'A/2024')
        self.assertFalse(
            self.Decision.decision_at(self.employee, '2025-06-30'),
            "след изтичането правото спира, не продължава")

    def test_an_open_ended_decision_never_expires(self):
        self._reshenie('2020-01-01', None, 90, 'C/2020')
        self.assertEqual(
            self.Decision.decision_at(self.employee, '2030-01-01').percent, 90,
            "празен срок значи пожизнено, не изтекло")

    # ── „няма" срещу „изтекло": двете различни положения ─────────────────

    def test_no_decision_differs_from_an_expired_one(self):
        """Едното иска подаване на документ, другото — преосвидетелстване."""
        self.assertFalse(self.employee.l10n_bg_telk_expired,
                         "без нито едно решение няма какво да е изтекло")
        self._reshenie('2020-01-01', '2020-12-31', 50, 'D/2020')
        self.employee.invalidate_recordset()
        self.assertFalse(self.employee.l10n_bg_telk_current_id,
                         "изтеклото не е действащо")
        self.assertTrue(self.employee.l10n_bg_telk_expired,
                        "но СЪЩЕСТВУВА — това не е липса")
        self.assertTrue(self.Decision.latest_for(self.employee),
                        "latest_for намира и изтеклото")

    def test_the_count_reaches_the_employee(self):
        self._reshenie('2024-01-01', '2025-12-31', 50, 'E/2024')
        self._reshenie('2026-01-01', None, 71, 'F/2026')
        self.employee.invalidate_recordset()
        self.assertEqual(self.employee.l10n_bg_telk_decision_count, 2)
        self.assertEqual(len(self.employee.l10n_bg_telk_decision_ids), 2)

    # ── гардовете на пренесения модел ─────────────────────────────────────

    def test_percent_is_whole_not_a_fraction(self):
        """🚨 Полигруп носеше 0,51 вместо 51 — гардът пази точно това.

        🚨 `assertRaises` на Odoo приема ЕДИН клас, не tuple: то прави
        `issubclass(exception, AccessError)` и на tuple гърми с
        „issubclass() arg 1 must be a class". Мерено 08.09.2026.
        """
        with self.assertRaises(ValidationError):
            self._reshenie('2026-01-01', None, 0, 'G/2026')

    def test_a_decision_cannot_expire_before_it_starts(self):
        with self.assertRaises(ValidationError):
            self._reshenie('2026-06-01', '2026-01-01', 50, 'H/2026')

    def test_the_same_number_twice_for_one_employee_is_refused(self):
        self._reshenie('2024-01-01', '2025-12-31', 50, 'I/2024')
        with self.assertRaises(Exception):
            self._reshenie('2026-01-01', None, 71, 'I/2024')

    def test_another_employee_may_hold_the_same_number(self):
        self._reshenie('2024-01-01', None, 50, 'J/2024')
        self._reshenie('2024-01-01', None, 50, 'J/2024', employee=self.drug)
        self.assertEqual(len(self.drug.l10n_bg_telk_decision_ids), 1)


@tagged('post_install', '-at_install', 'l10n_bg_telk')
class TestTelkDecisionChatter(TransactionCase):
    """Изгледът носи `<chatter/>`; моделът трябва да може да го обслужи.

    🚨 Без mail.thread отварянето на формата гърмеше с
    `_get_thread_with_access` (poligroup-v19, 08.09.2026) — а грешката идваше
    от web клиента, не от нашия код, тоест нито един наш тест не я хващаше.
    """

    def test_the_model_can_serve_a_chatter(self):
        employee = self.env["hr.employee"].create({"name": "ТЕЛК Chatter Test"})
        decision = self.env["l10n_bg.telk.decision"].create(
            {
                "employee_id": employee.id,
                "number": "TEST-CHATTER-1",
                "percent": 60,
                "date_from": "2026-01-01",
            }
        )
        # точно това вика web клиентът при отваряне на формата
        self.assertTrue(hasattr(decision, "_get_thread_with_access"))
        self.assertIn("message_ids", decision._fields)
        self.assertIn("activity_ids", decision._fields)

    def test_the_fields_that_move_rights_are_tracked(self):
        fields_ = self.env["l10n_bg.telk.decision"]._fields
        for name in ("number", "percent", "date_from", "date_to"):
            self.assertTrue(
                fields_[name].tracking,
                f"{name} changes the rights hanging on the decision and must be tracked",
            )
