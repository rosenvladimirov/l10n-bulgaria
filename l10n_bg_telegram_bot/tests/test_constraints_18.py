# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Портът към 18.0: уникалността е в _sql_constraints (models.Constraint е само
от 19.0). Пазачът при две едновременни доставки на едно и също обновление — в
базата, не само в проверката с SELECT."""
from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import TelegramBotCommon


@tagged("post_install", "-at_install")
class TestConstraints18(TelegramBotCommon):
    def _twice(self, model, vals):
        self.env[model].create(vals)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env[model].create(vals)

    def test_update_is_unique_in_the_database(self):
        self._twice("l10n.bg.telegram.update", {"bot_id": self.bot.id, "update_id": "4242"})

    def test_telegram_user_is_unique_per_bot(self):
        self._twice("l10n.bg.telegram.user", {"bot_id": self.bot.id, "telegram_id": "777000111"})

    def test_command_is_unique_per_bot(self):
        self._twice("l10n.bg.telegram.bot.command",
                    {"bot_id": self.bot.id, "command": "dup18", "description": "Duplicate"})
