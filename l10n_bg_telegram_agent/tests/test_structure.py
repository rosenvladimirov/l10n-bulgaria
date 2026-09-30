# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestTelegramAgentStructure(TransactionCase):
    def test_chat_is_unique_per_account(self):
        # В o19 `_sql_constraints` се игнорира — този тест пази, че ограничението
        # наистина е в базата
        account = self.env["telegram.account"].create({"name": "listener-1"})
        channel = self.env["telegram.channel"]
        channel.create({"account_id": account.id, "chat_id": "42"})
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(IntegrityError),
            self.env.cr.savepoint(),
        ):
            channel.create({"account_id": account.id, "chat_id": "42"})

    def test_menus_live_under_the_common_telegram_app(self):
        root = self.env.ref("l10n_bg_telegram_bot.l10n_bg_telegram_menu_root")
        self.assertFalse(root.parent_id, "Telegram is a top-level app")
        for xmlid in ("menu_telegram_sessions", "menu_telegram_accounts"):
            menu = self.env.ref(f"l10n_bg_telegram_agent.{xmlid}")
            self.assertEqual(menu.parent_id, root)
        manager = self.env.ref("l10n_bg_telegram_agent.group_telegram_agent_manager")
        self.assertIn(manager, root.group_ids)
        # Менютата на бота остават само за администратора
        bots = self.env.ref("l10n_bg_telegram_bot.l10n_bg_telegram_bot_menu")
        self.assertEqual(bots.group_ids, self.env.ref("base.group_system"))
