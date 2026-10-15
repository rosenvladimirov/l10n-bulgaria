# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

REQUESTS_POST = (
    "odoo.addons.l10n_bg_telegram_bot.models.l10n_bg_telegram_bot.requests.post"
)


def telegram_response(result=True, ok=True, description=None):
    response = MagicMock(status_code=200 if ok else 400)
    response.json.return_value = {
        "ok": ok,
        "result": result,
        "description": description,
    }
    return response


class TelegramBotCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bot = cls.env["l10n.bg.telegram.bot"].create(
            {
                "name": "Test Bot",
                "token": "123456:TEST-TOKEN",
                "welcome_message": "Hello from the test bot",
                "command_ids": [
                    (0, 0, {"command": "start", "description": "Start"}),
                    (0, 0, {"command": "help", "description": "List of commands"}),
                ],
            }
        )

    @staticmethod
    def make_update(update_id, text, user_id=987654321012, chat_id=None):
        return {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": "Ivan",
                    "last_name": "Petrov",
                    "username": "ivanp",
                    "language_code": "bg",
                },
                "chat": {"id": chat_id or user_id, "type": "private"},
                "date": 1790000000,
                "text": text,
            },
        }

    @contextmanager
    def mock_telegram(self, result=True):
        with patch(REQUESTS_POST, return_value=telegram_response(result)) as post:
            yield post

    @staticmethod
    def sent_texts(post):
        return [
            c.kwargs["json"]["text"]
            for c in post.call_args_list
            if c.args[0].endswith("/sendMessage")
        ]
