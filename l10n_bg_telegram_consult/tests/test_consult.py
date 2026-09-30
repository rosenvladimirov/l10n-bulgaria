# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

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
