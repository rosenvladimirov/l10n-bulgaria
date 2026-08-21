"""ДС-то пипа НОСИТЕЛИТЕ — длъжността и работното място, не производните им.

П4: длъжността в Odoo е `hr.job`; НКПД, КИД и квалификационната група се
произвеждат от нея. Дотук ДС-то пишеше само групата — производното — и МОД
излизаше като „ред = КИД (стар), колона = група (нова)", тоест хибрид, който
не отговаря на нито една реална длъжност.

П5: работното място е `hr.work.location` със свой адрес, от който се вади
ЕКАТТЕ. Кодът се КОПИРА при раждането на версията, а резолверът излиза рано,
щом полето е попълнено ⇒ уведомлението по чл. 62, ал. 5 КТ тръгваше със
старото населено място.

Мутационни проверки (21.08.2026):
· без `vals['job_id']` → `test_job_change_moves_the_carrier` пада;
· без `vals['l10n_bg_workplace_code'] = False` → `test_workplace_change_...`
  пада с наследения код.
"""
from datetime import date

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
