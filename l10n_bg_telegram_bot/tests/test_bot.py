# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import REQUESTS_POST, TelegramBotCommon, telegram_response


@tagged("post_install", "-at_install")
class TestTelegramBot(TelegramBotCommon):
    def test_start_creates_user_with_partner_and_replies(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(1, "/start"))
        user = self.bot.user_ids
        self.assertEqual(len(user), 1)
        # 13 цифри: над 32-битовия Integer — пази избора на Char
        self.assertEqual(user.telegram_id, "987654321012")
        self.assertEqual(user.partner_id.name, "Ivan Petrov")
        self.assertEqual(self.sent_texts(post), ["Hello from the test bot"])
        self.assertEqual(post.call_args.kwargs["json"]["chat_id"], "987654321012")

    def test_same_update_is_processed_once(self):
        update = self.make_update(2, "/start")
        with self.mock_telegram() as post:
            self.bot._handle_update(update)
            self.bot._handle_update(update)
        self.assertEqual(len(self.sent_texts(post)), 1)

    def test_help_lists_commands(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(3, "/help"))
        self.assertEqual(
            self.sent_texts(post), ["/start — Start\n/help — List of commands"]
        )

    def test_command_with_bot_suffix_in_group(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(4, "/HELP@test_bot"))
        self.assertIn("/start — Start", self.sent_texts(post)[0])

    def test_unknown_command_answers(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(5, "/nosuch arg"))
        self.assertIn("/nosuch", self.sent_texts(post)[0])

    def test_plain_text_is_logged_without_reply(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(6, "Имам въпрос за ДДС"))
        self.assertEqual(self.sent_texts(post), [])
        self.assertIn(
            "Имам въпрос за ДДС", self.bot.user_ids.message_ids.mapped("body")[0]
        )

    def test_known_user_is_updated_not_duplicated(self):
        with self.mock_telegram():
            self.bot._handle_update(self.make_update(7, "hi"))
            update = self.make_update(8, "hi again")
            update["message"]["from"]["username"] = "ivan_new"
            self.bot._handle_update(update)
        self.assertEqual(len(self.bot.user_ids), 1)
        self.assertEqual(self.bot.user_ids.username, "ivan_new")

    def test_messages_from_bots_are_ignored(self):
        update = self.make_update(9, "/start")
        update["message"]["from"]["is_bot"] = True
        with self.mock_telegram() as post:
            self.bot._handle_update(update)
        self.assertFalse(self.bot.user_ids)
        post.assert_not_called()

    @mute_logger("odoo.addons.l10n_bg_telegram_bot.models.l10n_bg_telegram_bot")
    def test_failing_handler_rolls_back_but_keeps_update(self):
        # Telegram отказва отговора ⇒ партньорът от /start не остава, update-ът — да
        partners_before = self.env["res.partner"].search_count([])
        with patch(
            REQUESTS_POST,
            return_value=telegram_response(ok=False, description="Forbidden"),
        ):
            self.bot._handle_update(self.make_update(10, "/start"))
        self.assertEqual(self.env["res.partner"].search_count([]), partners_before)
        self.assertFalse(self.bot.user_ids)
        self.assertTrue(
            self.env["l10n.bg.telegram.update"].search(
                [("bot_id", "=", self.bot.id), ("update_id", "=", "10")]
            )
        )

    def test_api_error_is_user_error_with_description(self):
        with (
            patch(
                REQUESTS_POST,
                return_value=telegram_response(ok=False, description="Unauthorized"),
            ),
            self.assertRaisesRegex(UserError, "Unauthorized"),
        ):
            self.bot.send_message("1", "x")

    def test_invalid_command_name(self):
        with self.assertRaises(ValidationError):
            self.bot.command_ids = [(0, 0, {"command": "Buy-Now", "description": "x"})]

    def test_set_webhook_requires_https(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "http://odoo.local"
        )
        with self.mock_telegram() as post, self.assertRaises(UserError):
            self.bot.action_set_webhook()
        post.assert_not_called()

    def test_set_webhook_sends_secret_and_updates(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://www.example.com"
        )
        with self.mock_telegram() as post:
            self.bot.action_set_webhook()
        payload = post.call_args.kwargs["json"]
        self.assertEqual(
            payload["url"],
            f"https://www.example.com/l10n_bg_telegram/webhook/{self.bot.id}",
        )
        self.assertEqual(payload["secret_token"], self.bot.webhook_secret)
        self.assertEqual(payload["allowed_updates"], ["message", "callback_query"])
        self.assertEqual(self.bot.webhook_state, "set")

    def test_sync_profile_pushes_commands(self):
        with self.mock_telegram(result={"username": "test_bot"}) as post:
            self.bot.action_sync_profile()
        self.assertEqual(self.bot.username, "test_bot")
        commands = next(
            c.kwargs["json"]["commands"]
            for c in post.call_args_list
            if c.args[0].endswith("/setMyCommands")
        )
        self.assertEqual([c["command"] for c in commands], ["start", "help"])

    def test_callback_query_dispatches_and_answers(self):
        calls = []
        bot_class = type(self.bot)
        bot_class._callback_ping = lambda bot, tg_user, arg: calls.append(
            (tg_user, arg)
        )
        self.addCleanup(delattr, bot_class, "_callback_ping")
        update = {
            "update_id": 20,
            "callback_query": {
                "id": "cb-1",
                "from": self.make_update(0, "")["message"]["from"],
                "message": {"chat": {"id": 987654321012}},
                "data": "ping:42",
            },
        }
        with self.mock_telegram() as post:
            self.bot._handle_update(update)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], "42")
        answered = [
            c for c in post.call_args_list if c.args[0].endswith("/answerCallbackQuery")
        ]
        self.assertEqual(answered[0].kwargs["json"], {"callback_query_id": "cb-1"})

    def test_unsafe_names_are_not_dispatched(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self.make_update(21, "/start.__class__"))
        self.assertIn("Unknown command", self.sent_texts(post)[0])
