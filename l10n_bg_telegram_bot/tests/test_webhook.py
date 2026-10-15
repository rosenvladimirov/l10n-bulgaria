# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from .common import REQUESTS_POST, TelegramBotCommon, telegram_response


@tagged("post_install", "-at_install")
class TestTelegramWebhook(TelegramBotCommon, HttpCase):
    def _post(self, bot_id, update, secret):
        headers = {"Content-Type": "application/json"}
        if secret is not None:
            headers["X-Telegram-Bot-Api-Secret-Token"] = secret
        return self.url_open(
            f"/l10n_bg_telegram/webhook/{bot_id}",
            data=json.dumps(update),
            headers=headers,
        )

    def test_webhook_with_secret_processes_update(self):
        with patch(REQUESTS_POST, return_value=telegram_response()) as post:
            response = self._post(
                self.bot.id, self.make_update(101, "/start"), self.bot.webhook_secret
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.bot.user_ids), 1)
        self.assertEqual(self.sent_texts(post), ["Hello from the test bot"])

    @mute_logger("odoo.addons.l10n_bg_telegram_bot.controllers.main", "odoo.http")
    def test_webhook_rejects_wrong_or_missing_secret(self):
        with patch(REQUESTS_POST, return_value=telegram_response()) as post:
            wrong = self._post(self.bot.id, self.make_update(102, "/start"), "wrong")
            missing = self._post(self.bot.id, self.make_update(103, "/start"), None)
        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(missing.status_code, 403)
        self.assertFalse(self.bot.user_ids)
        post.assert_not_called()

    @mute_logger("odoo.http")
    def test_webhook_unknown_or_archived_bot(self):
        self.assertEqual(
            self._post(
                self.bot.id + 1000, self.make_update(104, "/start"), "x"
            ).status_code,
            404,
        )
        self.bot.active = False
        self.assertEqual(
            self._post(
                self.bot.id, self.make_update(105, "/start"), self.bot.webhook_secret
            ).status_code,
            404,
        )
