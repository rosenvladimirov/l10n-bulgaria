# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged

from .common import TelegramBotCommon


@tagged("post_install", "-at_install")
class TestTelegramLanguage(TelegramBotCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("bg_BG")
        cls.bot.update_field_translations(
            "welcome_message", {"bg_BG": "Здравейте от тестовия бот"}
        )
        cls.bot.command_ids.filtered(
            lambda c: c.command == "help"
        ).update_field_translations("description", {"bg_BG": "Списък с командите"})

    def _update(self, update_id, text, language_code, user_id=987654321012):
        update = self.make_update(update_id, text, user_id=user_id)
        update["message"]["from"]["language_code"] = language_code
        return update

    def _record_reply_languages(self):
        """Кой език има контекстът при всеки отговор."""
        seen = []
        user_class = type(self.env["l10n.bg.telegram.user"])
        original = user_class._reply

        def _reply(user, text, **kwargs):
            seen.append(user.env.lang)
            return original(user, text, **kwargs)

        user_class._reply = _reply
        self.addCleanup(setattr, user_class, "_reply", original)
        return seen

    def test_start_answers_in_telegram_language_and_sets_partner_lang(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self._update(1, "/start", "bg"))
        self.assertEqual(self.sent_texts(post), ["Здравейте от тестовия бот"])
        self.assertEqual(self.bot.user_ids.partner_id.lang, "bg_BG")

    def test_other_client_gets_english(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self._update(2, "/start", "en", user_id=5))
        self.assertEqual(self.sent_texts(post), ["Hello from the test bot"])

    def test_code_strings_are_rendered_in_client_language(self):
        seen = self._record_reply_languages()
        with self.mock_telegram():
            self.bot._handle_update(self._update(3, "/nosuch", "bg"))
            self.bot._handle_update(self._update(4, "/nosuch", "en", user_id=6))
        self.assertEqual(seen, ["bg_BG", "en_US"])

    def test_unknown_language_falls_back_to_default(self):
        seen = self._record_reply_languages()
        with self.mock_telegram():
            self.bot._handle_update(self._update(5, "/help", "xx"))
        self.assertEqual(seen, ["en_US"])

    def test_regional_telegram_code_matches_installed_language(self):
        seen = self._record_reply_languages()
        with self.mock_telegram():
            self.bot._handle_update(self._update(6, "/help", "bg-BG"))
        self.assertEqual(seen, ["bg_BG"])

    def test_contact_language_overrides_telegram(self):
        with self.mock_telegram():
            self.bot._handle_update(self._update(7, "/start", "bg"))
        self.bot.user_ids.partner_id.lang = "en_US"
        seen = self._record_reply_languages()
        with self.mock_telegram():
            self.bot._handle_update(self._update(8, "/help", "bg"))
        self.assertEqual(seen, ["en_US"])

    def test_help_uses_translated_command_descriptions(self):
        with self.mock_telegram() as post:
            self.bot._handle_update(self._update(9, "/help", "bg"))
        self.assertIn("/help — Списък с командите", self.sent_texts(post)[0])

    def test_sync_profile_pushes_every_language(self):
        with self.mock_telegram(result={"username": "test_bot"}) as post:
            self.bot.action_sync_profile()
        commands = {
            c.kwargs["json"].get("language_code"): c.kwargs["json"]["commands"]
            for c in post.call_args_list
            if c.args[0].endswith("/setMyCommands")
        }
        self.assertEqual(set(commands), {None, "en", "bg"})
        help_bg = next(c for c in commands["bg"] if c["command"] == "help")
        help_default = next(c for c in commands[None] if c["command"] == "help")
        self.assertEqual(help_bg["description"], "Списък с командите")
        self.assertEqual(help_default["description"], "List of commands")
