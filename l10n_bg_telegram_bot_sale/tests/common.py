# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command

from odoo.addons.l10n_bg_telegram_bot.tests.common import TelegramBotCommon


class TelegramSaleCommon(TelegramBotCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env["website"].create(
            {"name": "Telegram Shop", "company_id": cls.env.company.id}
        )
        cls.salesperson = cls.env.ref("base.user_admin")
        cls.website.salesperson_id = cls.salesperson
        cls.hours = cls.env["product.product"].create(
            {
                "name": "Odoo Consulting — Prepaid Hours",
                "type": "service",
                "invoice_policy": "order",
                "service_type": "timesheet",
                "list_price": 50.0,
                "sale_ok": True,
                "taxes_id": [Command.clear()],
            }
        )
        cls.bot.write(
            {
                "website_id": cls.website.id,
                "package_ids": [
                    Command.create(
                        {"name": "10 hours", "product_id": cls.hours.id, "quantity": 10}
                    )
                ],
            }
        )
        cls.package = cls.bot.package_ids

    def start_user(self, update_id=1):
        """Регистрира потребителя през /start и връща записа му."""
        with self.mock_telegram():
            self.bot._handle_update(self.make_update(update_id, "/start"))
        return self.bot.user_ids

    def press(self, update_id, data):
        return {
            "update_id": update_id,
            "callback_query": {
                "id": f"cb-{update_id}",
                "from": self.make_update(0, "")["message"]["from"],
                "message": {"chat": {"id": 987654321012}},
                "data": data,
            },
        }

    def buy(self, update_id=2):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.press(update_id, f"buy:{self.package.id}"))
        return post

    @staticmethod
    def sent_markups(post):
        return [
            c.kwargs["json"].get("reply_markup")
            for c in post.call_args_list
            if c.args[0].endswith("/sendMessage")
        ]
