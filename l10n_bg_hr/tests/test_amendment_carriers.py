"""ДС-то пипа НОСИТЕЛИТЕ — длъжността и работното място, не производните им.

П4: длъжността в Odoo е `hr.job`; НКПД, КИД и квалификационната група се
произвеждат от нея. Дотук ДС-то пишеше само групата — производното — и МОД
излизаше като „ред = КИД (стар), колона = група (нова)", тоест хибрид, който
не отговаря на нито една реална длъжност.

П5: работното място е `hr.work.location` със свой адрес, от който се вади
ЕКАТТЕ. Кодът се КОПИРА при раждането на версията, а резолверът излиза рано,
щом полето е попълнено ⇒ уведомлението по чл. 62, ал. 5 КТ тръгваше със
старото населено място.

DEF-107 (30.08.2026, Пламена): механизмът беше приет, но НИТО ЕДИН изглед не
предлагаше `new_job_id` — нула срещания по `*.xml` в целия стек, а визардният
модел изобщо нямаше полето. Тоест работещ механизъм без носител: през
интерфейса се стигаше само до шифъра, който после се връща тихо.

Мутационни проверки (21.08.2026):
· без `vals['job_id']` → `test_job_change_moves_the_carrier` пада;
· без `vals['l10n_bg_workplace_code'] = False` → `test_workplace_change_...`
  пада с наследения код.
Мутационни проверки (31.08.2026):
· махни `new_job_id` от кой да е от двата изгледа → `test_both_views_offer_...`
  пада (точно състоянието отпреди поправката);
· махни преноса от `action_create_amendment` → `test_wizard_carries_the_job...`
  пада.
"""
from datetime import date, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAmendmentCarriers(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.employee = cls.env["hr.employee"].create({"name": "Тест Носители"})
        cls.version = cls.employee.version_id

        cls.job_staro = cls.env["hr.job"].create({"name": "Работник"})
        cls.job_novo = cls.env["hr.job"].create({"name": "Бригадир"})

        partner_staro = cls.env["res.partner"].create({
            "name": "Цех Изток", "city": "Пловдив",
        })
        partner_novo = cls.env["res.partner"].create({
            "name": "Цех Запад", "city": "Русе",
        })
        cls.location_staro = cls.env["hr.work.location"].create({
            "name": "Изток", "address_id": partner_staro.id,
        })
        cls.location_novo = cls.env["hr.work.location"].create({
            "name": "Запад", "address_id": partner_novo.id,
        })

        cls.version.write({
            "wage": 1000.0,
            "job_id": cls.job_staro.id,
            "address_id": partner_staro.id,
            "work_location_id": cls.location_staro.id,
            "l10n_bg_workplace_code": "56784",  # ЕКАТТЕ на старото място
        })

    def _activate(self, vals):
        amd = self.env["l10n_bg.hr.version.amendment"].create(dict({
            "version_id": self.version.id,
            "date_signed": date(2026, 2, 1),
            "date_effective": date(2026, 3, 1),
            "subject": "Тест носители",
        }, **vals))
        amd.action_submit_for_approval()
        amd.action_approve()
        amd.action_activate()
        return amd

    def test_job_change_moves_the_carrier(self):
        """ДС за длъжност сменя самата длъжност, не само групата."""
        amd = self._activate({
            "amendment_type": "position_change",
            "new_job_id": self.job_novo.id,
        })
        nova = amd.applied_version_id
        self.assertTrue(nova, "П1 не работи — няма приложена версия")
        self.assertEqual(
            nova.job_id, self.job_novo,
            "длъжността не е сменена — МОД ще се вади срещу старата длъжност")
        self.assertEqual(
            self.version.job_id, self.job_staro,
            "изходната версия не бива да се мени — тя е историята")

    def test_job_snapshot_records_the_previous_job(self):
        """Бланката иска „предишна длъжност“ — щампова се при одобрението."""
        amd = self.env["l10n_bg.hr.version.amendment"].create({
            "version_id": self.version.id,
            "amendment_type": "position_change",
            "date_signed": date(2026, 2, 1),
            "date_effective": date(2026, 3, 1),
            "subject": "Тест щампа",
            "new_job_id": self.job_novo.id,
        })
        amd.action_submit_for_approval()
        amd.action_approve()
        self.assertEqual(
            amd.old_job_id, self.job_staro,
            "предишната длъжност не е щампована — бланката ще излезе без нея")

    def test_workplace_change_moves_carrier_and_clears_ekatte(self):
        """ДС за място сменя записа, адреса, и НЕ пренася стария ЕКАТТЕ."""
        amd = self._activate({
            "amendment_type": "workplace_change",
            "new_work_location_id": self.location_novo.id,
        })
        nova = amd.applied_version_id
        self.assertEqual(
            nova.work_location_id, self.location_novo,
            "работното място не е сменено")
        self.assertEqual(
            nova.address_id, self.location_novo.address_id,
            "адресът не следва локацията — ядреният домейн иска двойката "
            "да е съгласувана")
        self.assertFalse(
            nova.l10n_bg_workplace_code,
            "ЕКАТТЕ кодът е наследен от старото място: уведомлението по "
            "чл. 62, ал. 5 КТ ще тръгне със старото населено място")
        self.assertEqual(
            self.version.l10n_bg_workplace_code, "56784",
            "изходната версия не бива да си губи кода")

    def test_text_only_workplace_is_not_applied(self):
        """Свободният текст не е носител — не мени нищо по версията.

        Текстът не произвежда нито една промяна по версията, тъй че ДС-то
        няма какво да приложи и активирането се ОТКАЗВА. Дотук излизаше тихо
        и въпреки това ставаше „в сила".
        """
        amd = self.env["l10n_bg.hr.version.amendment"].create({
            "version_id": self.version.id,
            "amendment_type": "workplace_change",
            "date_signed": date(2026, 2, 1),
            "date_effective": date(2026, 3, 1),
            "subject": "Тест носители",
            "new_work_location": "някъде другаде",
        })
        amd.action_submit_for_approval()
        amd.action_approve()
        with self.assertRaises(ValidationError):
            amd.action_activate()
        self.assertFalse(
            amd.applied_version_id,
            "ДС без нито една реална промяна не бива да ражда версия")
        self.assertEqual(
            self.version.work_location_id, self.location_staro,
            "текстът е сменил носителя — не бива")
        self.assertEqual(
            self.version.l10n_bg_workplace_code, "56784",
            "текстът е занулил ЕКАТТЕ кода — зануляването принадлежи само на "
            "смяната през записа")

    # =========================================================================
    # DEF-107 — НОСИТЕЛЯТ В ИНТЕРФЕЙСА
    # =========================================================================

    def test_both_views_offer_the_job_carrier(self):
        """Механизъм без носител в изгледа е механизъм, до който не се стига.

        Мери се СГЛОБЕНИЯТ arch през `get_view`, не изходният XML: така
        проверката хваща и счупен xpath от наследник, който би махнал полето
        мълчаливо.
        """
        for model, view in (
                ("l10n_bg.hr.version.amendment",
                 "l10n_bg_hr.view_l10n_bg_hr_contract_amendment_form"),
                ("l10n_bg.hr.version.amendment.wizard",
                 "l10n_bg_hr.view_hr_version_amendment_wizard_form")):
            arch = self.env[model].get_view(self.env.ref(view).id, "form")["arch"]
            self.assertIn(
                "new_job_id", arch,
                "%s не предлага длъжността — през този изглед се стига само "
                "до шифъра по НКПД, който първото опресняване връща тихо"
                % view)

    def test_wizard_carries_the_job_to_the_amendment(self):
        """Визардът пренася длъжността, не само производния ѝ шифър."""
        wiz = self.env["l10n_bg.hr.version.amendment.wizard"].create({
            "employee_id": self.employee.id,
            "version_id": self.version.id,
            "amendment_type": "position_change",
            "subject": "Тест визард",
            # 🚨 Визардът ЗАШИВА `date_signed = today()` (виж
            # `hr_version_amendment_wizard.py`), тъй че дата на влизане
            # в сила в МИНАЛОТО минава за „подписано след влизането" и
            # гардът отказва. Тук датата е вход на визарда, не носител —
            # взима се в бъдещето и относително, за да не изгние догодина.
            "date_effective": date.today() + timedelta(days=30),
            "new_job_id": self.job_novo.id,
        })
        amd = self.env["l10n_bg.hr.version.amendment"].browse(
            wiz.action_create_amendment()["res_id"])
        self.assertEqual(
            amd.new_job_id, self.job_novo,
            "визардът е изгубил длъжността по пътя към ДС-то")
        self.assertEqual(
            amd.old_job_id, self.job_staro,
            "визардът не е щампувал предишната длъжност")

    def test_code_only_amendment_leaves_a_trace(self):
        """Заварената пътека остава проходима, но вече не мълчи."""
        shifar = self.env["bg.hr.payroll.ncop.classification"].search([], limit=1)
        if not shifar:
            self.skipTest("няма зареден НКПД класификатор")
        amd = self._activate({
            "amendment_type": "position_change",
            "new_position_id": shifar.id,
        })
        telata = amd.message_ids.mapped("body")
        self.assertTrue(
            any("NKPD" in t or "НКПД" in t for t in telata),
            "ДС само с шифър мина без следа в чатъра — точно тишината, "
            "заради която дефектът стигна до живи записи")

    # =========================================================================
    # DEF-116/1в — ВИЗАРДЪТ ПОКРИВА ТИПОВЕТЕ, КОИТО ПРЕДЛАГА
    # =========================================================================

    def test_wizard_offers_the_end_date_it_demands(self):
        """Отказ, който няма къде да бъде удовлетворен, е задънена улица.

        `action_create_amendment` отказва „Временно преместване" без крайна
        дата, а полето беше само на модела — в изгледа нула срещания.
        Мутация: махни `date_end` от изгледа → пада.
        """
        arch = self.env["l10n_bg.hr.version.amendment.wizard"].get_view(
            self.env.ref("l10n_bg_hr.view_hr_version_amendment_wizard_form").id,
            "form")["arch"]
        self.assertIn(
            'name="date_end"', arch,
            "визардът иска крайна дата, но не я предлага — „Временно "
            "преместване“ не може да бъде създадено през интерфейса")

    def test_other_does_not_open_every_tab(self):
        """„Друго изменение" отваряше ВСИЧКИТЕ пет таба наведнъж."""
        arch = self.env["l10n_bg.hr.version.amendment.wizard"].get_view(
            self.env.ref("l10n_bg_hr.view_hr_version_amendment_wizard_form").id,
            "form")["arch"]
        self.assertNotIn(
            "'wage_change', 'other'", arch,
            "табът за заплата още се отваря от „Друго“")
        self.assertIn(
            'name="description"', arch,
            "„Друго“ няма нито едно поле за съдържание")

    def test_wizard_carries_the_description(self):
        """Свободният текст стига до ДС-то, не спира във визарда."""
        wiz = self.env["l10n_bg.hr.version.amendment.wizard"].create({
            "employee_id": self.employee.id,
            "version_id": self.version.id,
            "amendment_type": "other",
            "subject": "Тест описание",
            # същото като в горния визард-тест: `date_signed` е зашито на
            # днес, тъй че миналата дата не минава гарда
            "date_effective": date.today() + timedelta(days=30),
            "description": "<p>Уговорка на свободен текст</p>",
        })
        amd = self.env["l10n_bg.hr.version.amendment"].browse(
            wiz.action_create_amendment()["res_id"])
        self.assertIn(
            "свободен текст", (amd.description or ""),
            "описанието не е пренесено — ДС-то излиза с празно тяло")

