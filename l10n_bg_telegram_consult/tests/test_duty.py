# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_bg_telegram_bot_sale.tests.common import TelegramSaleCommon

MANAGER_ID = 111222333444


@tagged("post_install", "-at_install")
class TestTelegramDuty(TelegramSaleCommon):
    """„Работиш за S00001“: групата е консултантът и клиентът, Odoo държи часовника."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project = cls.env["project.project"].create(
            {"name": "Consultations", "allow_billable": True, "allow_timesheets": True}
        )
        cls.hours.write(
            {
                "uom_id": cls.env.ref("uom.product_uom_hour").id,
                "service_tracking": "task_global_project",
                "project_id": project.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Consultant"})
        cls.bot.consult_employee_id = cls.employee

    def setUp(self):
        super().setUp()
        with self.mock_telegram():
            self.bot._handle_update(self.make_update(90, "/start", user_id=MANAGER_ID))
        self.manager = self.bot.user_ids.filtered(
            lambda u: u.telegram_id == str(MANAGER_ID)
        )
        self.bot.consult_manager_id = self.manager
        self.client = self.start_user() - self.manager
        self.buy()
        self.order = self.env["sale.order"].search(
            [("l10n_bg_telegram_user_id", "=", self.client.id)]
        )
        self.order.action_confirm()

    def _chat_ids(self, post):
        return [
            c.kwargs["json"]["chat_id"]
            for c in post.call_args_list
            if c.args[0].endswith("/sendMessage")
        ]

    def test_payload_is_client_without_bot(self):
        payload = self.order.l10n_bg_duty_payload()
        self.assertEqual(payload["members"], ["@ivanp"])
        self.assertEqual(payload["bot_username"], "")
        self.assertIn(self.order.name, payload["title"])

    def test_group_link_goes_to_client_through_the_bot(self):
        with self.mock_telegram() as post:
            self.order.l10n_bg_set_duty_group("-100555", "https://t.me/+s")
        self.assertEqual(self.order.l10n_bg_telegram_group_chat_id, "-100555")
        self.assertEqual(self._chat_ids(post), [self.client.chat_id])
        button = self.sent_markups(post)[0]["inline_keyboard"][0][0]
        self.assertEqual(button["url"], "https://t.me/+s")

    def test_start_needs_group_and_reports_remaining(self):
        with self.assertRaises(UserError):
            self.order.l10n_bg_duty_start()
        with self.mock_telegram():
            self.order.l10n_bg_set_duty_group("-100555", False)
        status = self.order.l10n_bg_duty_start()
        self.assertEqual(status["duty_state"], "on")
        self.assertEqual(status["chat_id"], "-100555")
        self.assertAlmostEqual(status["remaining_minutes"], 600, delta=1)

    def test_stop_logs_rounded_time_on_the_order_task(self):
        with self.mock_telegram():
            self.order.l10n_bg_set_duty_group("-100555", False)
        self.order.l10n_bg_duty_start()
        self.order.l10n_bg_duty_started = fields.Datetime.now() - timedelta(minutes=20)
        self.order.l10n_bg_duty_stop()
        task = self.order.order_line.task_id
        line = self.env["account.analytic.line"].search([("task_id", "=", task.id)])
        self.assertEqual(line.unit_amount, 0.5)
        self.assertEqual(line.employee_id, self.employee)
        self.assertEqual(self.order.l10n_bg_duty_state, "off")
        self.assertAlmostEqual(self.order.l10n_bg_duty_remaining_hours, 9.5)

    def test_cron_warns_client_then_stops_and_tells_manager(self):
        with self.mock_telegram():
            self.order.l10n_bg_set_duty_group("-100555", False)
        self.order.l10n_bg_duty_start()
        task = self.order.order_line.task_id
        self.env["account.analytic.line"].create(
            {
                "name": "used",
                "task_id": task.id,
                "project_id": task.project_id.id,
                "employee_id": self.employee.id,
                "unit_amount": 9,
            }
        )
        self.order.l10n_bg_duty_started = fields.Datetime.now() - timedelta(minutes=50)
        with self.mock_telegram() as post:
            self.order._cron_l10n_bg_duty_watch()
            self.order._cron_l10n_bg_duty_watch()
        self.assertEqual(self._chat_ids(post), [self.client.chat_id], "warned once")
        self.assertEqual(self.order.l10n_bg_duty_state, "on")
        self.order.l10n_bg_duty_started = fields.Datetime.now() - timedelta(minutes=65)
        with self.mock_telegram() as post:
            self.order._cron_l10n_bg_duty_watch()
        self.assertEqual(self.order.l10n_bg_duty_state, "off")
        self.assertEqual(
            sorted(self._chat_ids(post)),
            sorted([self.client.chat_id, self.manager.chat_id]),
        )
        # Изразходвано: 9 ч + 1 ч (таванът е остатъкът, не 1,25 ч)
        self.assertAlmostEqual(self.order.l10n_bg_duty_remaining_hours, 0.0)

    def test_order_without_prepaid_hours_cannot_start(self):
        other = self.env["sale.order"].create(
            {
                "partner_id": self.client.partner_id.id,
                "order_line": [
                    Command.create({"product_id": self.hours.id, "product_uom_qty": 1})
                ],
            }
        )
        with self.assertRaises(UserError):
            other.l10n_bg_duty_start()
