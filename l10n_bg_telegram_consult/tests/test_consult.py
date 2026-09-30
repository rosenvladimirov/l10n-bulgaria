# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_bg_telegram_bot_sale.tests.common import TelegramSaleCommon

MANAGER_ID = 111222333444


@tagged("post_install", "-at_install")
class TestTelegramConsult(TelegramSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project = cls.env["project.project"].create(
            {"name": "Consultations", "allow_billable": True, "allow_timesheets": True}
        )
        # Като истинския продукт: часове — иначе sale_timesheet не смята remaining_hours
        cls.hours.write(
            {
                "uom_id": cls.env.ref("uom.product_uom_hour").id,
                "service_tracking": "task_global_project",
                "project_id": project.id,
            }
        )

    def setUp(self):
        super().setUp()
        with self.mock_telegram():
            self.bot._handle_update(self.make_update(90, "/start", user_id=MANAGER_ID))
        self.manager = self.bot.user_ids.filtered(
            lambda u: u.telegram_id == str(MANAGER_ID)
        )
        self.bot.consult_manager_id = self.manager
        self.client = self.start_user()
        self.client = self.bot.user_ids - self.manager

    def _paid_hours(self, update_id=2):
        self.buy(update_id)
        order = self.env["sale.order"].search(
            [("l10n_bg_telegram_user_id", "=", self.client.id)],
            order="id desc",
            limit=1,
        )
        order.action_confirm()
        return order

    def _consult(self, update_id, text):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(update_id, text))
        return post

    def _press(self, update_id, data, user_id):
        update = self.press(update_id, data)
        update["callback_query"]["from"]["id"] = user_id
        with self.mock_telegram() as post:
            self.bot._handle_update(update)
        return post

    def _chat_ids(self, post):
        return [
            c.kwargs["json"]["chat_id"]
            for c in post.call_args_list
            if c.args[0].endswith("/sendMessage")
        ]

    def test_consult_without_prepaid_hours_asks_to_buy(self):
        post = self._consult(30, "/consult VAT return")
        self.assertIn("/buy", self.sent_texts(post)[0])
        self.assertFalse(self.env["l10n.bg.telegram.consult.request"].search([]))

    def test_consult_creates_request_on_paid_hours_and_notifies_manager(self):
        order = self._paid_hours()
        post = self._consult(31, "/consult VAT return for Q3 @anna @petar")
        request = self.env["l10n.bg.telegram.consult.request"].search([])
        self.assertEqual(len(request), 1)
        self.assertEqual(request.topic, "VAT return for Q3")
        self.assertEqual(request.participants, "@anna @petar")
        self.assertEqual(request.sale_line_id, order.order_line)
        self.assertTrue(request.task_id, "sale_project must have created the task")
        # Отговор на клиента и известие до отговорника
        self.assertEqual(
            self._chat_ids(post), [self.client.chat_id, self.manager.chat_id]
        )
        buttons = self.sent_markups(post)[1]["inline_keyboard"][0]
        self.assertEqual(buttons[0]["callback_data"], f"cok:{request.id}")

    def test_only_manager_can_approve_from_telegram(self):
        self._paid_hours()
        self._consult(32, "/consult Payroll")
        request = self.env["l10n.bg.telegram.consult.request"].search([])
        self._press(33, f"cok:{request.id}", int(self.client.telegram_id))
        self.assertEqual(request.state, "new")
        post = self._press(34, f"cok:{request.id}", MANAGER_ID)
        self.assertEqual(request.state, "approved")
        self.assertIn(self.client.chat_id, self._chat_ids(post))

    def test_group_is_linked_and_invite_sent(self):
        self._paid_hours()
        self._consult(35, "/consult Stock @anna")
        request = self.env["l10n.bg.telegram.consult.request"].search([])
        # С mock: иначе UserError идва от истинския Telegram, не от проверката
        with self.mock_telegram() as post, self.assertRaises(UserError):
            request.l10n_bg_set_group("-100123")
        post.assert_not_called()
        self.assertEqual(request.state, "new")
        self.assertFalse(request.group_chat_id)
        with self.mock_telegram():
            request.action_approve()
        payload = request.l10n_bg_consult_payload()[0]
        self.assertEqual(payload["members"], ["anna", "ivanp"])
        with self.mock_telegram() as post:
            request.l10n_bg_set_group("-100123", "https://t.me/+abc")
        self.assertEqual(request.state, "group")
        self.assertEqual(request.group_chat_id, "-100123")
        button = self.sent_markups(post)[0]["inline_keyboard"][0][0]
        self.assertEqual(button["url"], "https://t.me/+abc")

    def test_reject_informs_client(self):
        self._paid_hours()
        self._consult(36, "/consult Something")
        request = self.env["l10n.bg.telegram.consult.request"].search([])
        post = self._press(37, f"cno:{request.id}", MANAGER_ID)
        self.assertEqual(request.state, "rejected")
        self.assertIn(self.client.chat_id, self._chat_ids(post))

    def test_topic_is_required(self):
        self._paid_hours()
        post = self._consult(38, "/consult @anna")
        self.assertIn("Describe the topic", self.sent_texts(post)[0])

    def test_notifications_follow_each_recipient_language(self):
        self.env["res.lang"]._activate_lang("bg_BG")
        self.client.partner_id.lang = "bg_BG"
        self.manager._ensure_partner()
        self.manager.partner_id.lang = "en_US"
        self._paid_hours()
        seen = []
        user_class = type(self.env["l10n.bg.telegram.user"])
        original = user_class._reply

        def _reply(user, text, **kwargs):
            seen.append((user, user.env.lang))
            return original(user, text, **kwargs)

        user_class._reply = _reply
        self.addCleanup(setattr, user_class, "_reply", original)
        self._consult(40, "/consult ДДС")
        self.assertEqual(seen, [(self.client, "bg_BG"), (self.manager, "en_US")])
        request = self.env["l10n.bg.telegram.consult.request"].search([])
        seen.clear()
        # Одобрение от Odoo, от потребител на английски — клиентът пак е на български
        with self.mock_telegram():
            request.with_context(lang="en_US").action_approve()
        self.assertEqual(seen, [(self.client, "bg_BG")])

    def test_consult_uses_hours_of_order_moved_to_another_contact(self):
        order = self._paid_hours()
        order.partner_id = self.env["res.partner"].create({"name": "Shop login"})
        self._consult(41, "/consult Accounting")
        request = self.env["l10n.bg.telegram.consult.request"].search([])
        self.assertEqual(request.sale_line_id, order.order_line)

    # --- дежурство ---------------------------------------------------------

    def _group_request(self):
        """Одобрена заявка с група и отговорник-служител — готова за дежурство."""
        self._paid_hours()
        self._consult(50, "/consult Payroll")
        request = self.env["l10n.bg.telegram.consult.request"].search([])
        with self.mock_telegram():
            request.action_approve()
            request.l10n_bg_set_group("-100999", "https://t.me/+g")
        self.bot.consult_employee_id = self.env["hr.employee"].create(
            {"name": "Consultant"}
        )
        return request

    def _group_update(self, update_id, text, user_id=987654321012):
        update = self.make_update(update_id, text, user_id=user_id, chat_id=-100999)
        update["message"]["chat"]["type"] = "supergroup"
        return update

    def test_group_messages_are_stored_for_the_duty(self):
        request = self._group_request()
        with self.mock_telegram() as post:
            self.bot._handle_update(self._group_update(51, "How do I close the month?"))
        post.assert_not_called()
        message = request.consult_message_ids.filtered(lambda m: m.direction == "in")
        self.assertEqual(message.text, "How do I close the month?")
        self.assertEqual(message.telegram_message_id, "51")
        self.assertEqual(request.l10n_bg_duty_poll(0)["messages"][0]["id"], message.id)

    def test_duty_needs_employee_and_reports_remaining_minutes(self):
        request = self._group_request()
        self.bot.consult_employee_id = False
        with self.assertRaises(UserError):
            request.l10n_bg_duty_start()
        self.bot.consult_employee_id = self.env["hr.employee"].create({"name": "C"})
        status = request.l10n_bg_duty_start()
        self.assertEqual(status["duty_state"], "on")
        self.assertAlmostEqual(status["remaining_minutes"], 600, delta=1)

    def test_draft_goes_to_manager_and_only_manager_can_send_it(self):
        request = self._group_request()
        request.l10n_bg_duty_start()
        with self.mock_telegram():
            self.bot._handle_update(self._group_update(52, "Question?"))
        question = request.consult_message_ids.filtered(lambda m: m.direction == "in")
        with self.mock_telegram() as post:
            draft_id = request.l10n_bg_duty_draft("Answer.", question.id)
        # Черновата е в личния чат на отговорника, не в групата
        self.assertEqual(self._chat_ids(post), [self.manager.chat_id])
        self.assertEqual(
            self.sent_markups(post)[0]["inline_keyboard"][0][0]["callback_data"],
            f"cds:{draft_id}",
        )
        draft = self.env["l10n.bg.telegram.consult.message"].browse(draft_id)
        self._press(53, f"cds:{draft_id}", int(self.client.telegram_id))
        self.assertEqual(draft.state, "draft")
        post = self._press(54, f"cds:{draft_id}", MANAGER_ID)
        self.assertEqual(draft.state, "sent")
        sent = [
            c.kwargs["json"]
            for c in post.call_args_list
            if c.args[0].endswith("/sendMessage")
            and c.kwargs["json"]["chat_id"] == "-100999"
        ]
        self.assertEqual(sent[0]["text"], "Answer.")
        self.assertEqual(sent[0]["reply_parameters"]["message_id"], 52)

    def test_stop_logs_rounded_time_on_the_task(self):
        request = self._group_request()
        request.l10n_bg_duty_start()
        request.duty_started = fields.Datetime.now() - timedelta(minutes=20)
        request.l10n_bg_duty_stop()
        line = self.env["account.analytic.line"].search(
            [("task_id", "=", request.task_id.id)]
        )
        self.assertEqual(line.unit_amount, 0.5)
        self.assertEqual(line.employee_id, self.bot.consult_employee_id)
        self.assertEqual(request.duty_state, "off")
        self.assertAlmostEqual(request.remaining_hours, 9.5)

    def test_cron_warns_then_stops_when_time_is_used_up(self):
        request = self._group_request()
        # Един час остатък: купуваме пакет, изразходваме 9 ч
        request.l10n_bg_duty_start()
        self.env["account.analytic.line"].create(
            {
                "name": "used",
                "task_id": request.task_id.id,
                "project_id": request.task_id.project_id.id,
                "employee_id": self.bot.consult_employee_id.id,
                "unit_amount": 9,
            }
        )
        request.duty_started = fields.Datetime.now() - timedelta(minutes=50)
        with self.mock_telegram() as post:
            request._cron_duty_watch()
            request._cron_duty_watch()
        warnings = [c for c in self._chat_ids(post) if c == "-100999"]
        self.assertEqual(len(warnings), 1, "warned once")
        self.assertEqual(request.duty_state, "on")
        request.duty_started = fields.Datetime.now() - timedelta(minutes=65)
        with self.mock_telegram() as post:
            request._cron_duty_watch()
        self.assertEqual(request.duty_state, "off")
        self.assertIn("-100999", self._chat_ids(post))
        self.assertIn(self.manager.chat_id, self._chat_ids(post))
