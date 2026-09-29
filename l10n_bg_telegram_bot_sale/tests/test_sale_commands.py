# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.tests import tagged

from .common import TelegramSaleCommon


@tagged("post_install", "-at_install")
class TestTelegramSaleCommands(TelegramSaleCommon):
    def test_buy_offers_package_buttons(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(11, "/buy"))
        keyboard = self.sent_markups(post)[0]["inline_keyboard"]
        self.assertEqual(
            keyboard,
            [[{"text": "10 hours", "callback_data": f"buy:{self.package.id}"}]],
        )

    def test_pressing_package_creates_shop_order_with_pay_link(self):
        tg_user = self.start_user()
        post = self.buy()
        order = self.env["sale.order"].search(
            [("l10n_bg_telegram_user_id", "=", tg_user.id)]
        )
        self.assertEqual(len(order), 1)
        self.assertEqual(order.partner_id, tg_user.partner_id)
        self.assertEqual(order.website_id, self.website)
        # Продавачът е от сайта, не публичният потребител на webhook-а
        self.assertEqual(order.user_id, self.salesperson)
        self.assertEqual(order.order_line.product_id, self.hours)
        self.assertEqual(order.order_line.product_uom_qty, 10)
        button = self.sent_markups(post)[0]["inline_keyboard"][0][0]
        self.assertTrue(
            button["url"].endswith(
                f"/l10n_bg_telegram/pay/{order.id}/{order.access_token}"
            )
        )

    def test_package_of_another_bot_is_refused(self):
        self.start_user()
        other = self.env["l10n.bg.telegram.bot"].create(
            {
                "name": "Other",
                "token": "1:X",
                "package_ids": [
                    Command.create(
                        {"name": "x", "product_id": self.hours.id, "quantity": 1}
                    )
                ],
            }
        )
        with self.mock_telegram() as post:
            self.bot._handle_update(self.press(3, f"buy:{other.package_ids.id}"))
        self.assertFalse(
            self.env["sale.order"].search([("l10n_bg_telegram_user_id", "!=", False)])
        )
        self.assertIn("no longer available", self.sent_texts(post)[0])

    def test_voucher_applies_promo_code_to_last_unpaid_order(self):
        self.env["loyalty.program"].create(
            {
                "name": "TG 10%",
                "program_type": "promo_code",
                "trigger": "with_code",
                "applies_on": "current",
                "rule_ids": [Command.create({"mode": "with_code", "code": "TG10"})],
                "reward_ids": [
                    Command.create(
                        {
                            "reward_type": "discount",
                            "discount": 10,
                            "discount_mode": "percent",
                            "discount_applicability": "order",
                        }
                    )
                ],
            }
        )
        tg_user = self.start_user()
        self.buy()
        order = self.env["sale.order"].search(
            [("l10n_bg_telegram_user_id", "=", tg_user.id)]
        )
        self.assertAlmostEqual(order.amount_total, 500.0)
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(12, "/voucher TG10"))
        self.assertAlmostEqual(order.amount_total, 450.0)
        self.assertIn("Voucher applied", self.sent_texts(post)[0])

    def test_voucher_with_unknown_code_answers_the_error(self):
        self.start_user()
        self.buy()
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(13, "/voucher NOPE"))
        self.assertIn("invalid", self.sent_texts(post)[0])

    def test_voucher_without_order(self):
        self.start_user()
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(14, "/voucher TG10"))
        self.assertIn("/buy", self.sent_texts(post)[0])

    def test_balance_counts_confirmed_prepaid_hours_and_ewallet(self):
        tg_user = self.start_user()
        self.buy()
        order = self.env["sale.order"].search(
            [("l10n_bg_telegram_user_id", "=", tg_user.id)]
        )
        order.action_confirm()
        # Непотвърдена поръчка не се брои
        self.buy(update_id=4)
        program = self.env["loyalty.program"].create(
            {
                "name": "Wallet",
                "program_type": "ewallet",
                "trigger": "auto",
                "applies_on": "future",
            }
        )
        self.env["loyalty.card"].create(
            {
                "program_id": program.id,
                "partner_id": tg_user.partner_id.id,
                "points": 25,
            }
        )
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(15, "/balance"))
        text = self.sent_texts(post)[0]
        self.assertIn("10.00 left", text)
        self.assertIn("Wallet: 25.00", text)

    def test_orders_lists_and_offers_pay_only_for_unpaid(self):
        tg_user = self.start_user()
        self.buy()
        paid = self.env["sale.order"].search(
            [("l10n_bg_telegram_user_id", "=", tg_user.id)]
        )
        paid.action_confirm()
        self.buy(update_id=5)
        unpaid = self.env["sale.order"].search(
            [("l10n_bg_telegram_user_id", "=", tg_user.id), ("state", "=", "draft")]
        )
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(16, "/orders"))
        self.assertIn(paid.name, self.sent_texts(post)[0])
        self.assertIn(unpaid.name, self.sent_texts(post)[0])
        buttons = self.sent_markups(post)[0]["inline_keyboard"]
        self.assertEqual(len(buttons), 1)
        self.assertIn(unpaid.name, buttons[0][0]["text"])
