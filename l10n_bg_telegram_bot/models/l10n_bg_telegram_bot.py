# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import re
import secrets

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import urls

_logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
API_TIMEOUT = 15
WEBHOOK_ROUTE = "/l10n_bg_telegram/webhook"
# Update типовете, които ботът приема; останалите Telegram не ги праща изобщо
ALLOWED_UPDATES = ["message", "callback_query"]
# Името на команда/бутон отива в getattr ⇒ само това, което Telegram допуска
SAFE_NAME = re.compile(r"[a-z0-9_]{1,32}")


class L10nBgTelegramBot(models.Model):
    _name = "l10n.bg.telegram.bot"
    _description = "Telegram Bot"
    _inherit = "mail.thread"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    token = fields.Char(
        string="Bot Token",
        help="Token issued by @BotFather. Keep it secret.",
        groups="base.group_system",
        copy=False,
    )
    webhook_secret = fields.Char(
        help="Sent by Telegram in the X-Telegram-Bot-Api-Secret-Token header "
        "and checked on every update.",
        groups="base.group_system",
        copy=False,
        default=lambda self: secrets.token_urlsafe(32),
    )
    username = fields.Char(
        readonly=True, help="Bot username, read from Telegram (getMe)."
    )
    description = fields.Text(
        help="Shown in an empty chat before the user presses Start (max 512 chars).",
        translate=True,
    )
    short_description = fields.Char(
        help="Shown on the bot profile page (max 120 chars).", translate=True
    )
    welcome_message = fields.Text(
        help="Reply to /start.", translate=True, default="Welcome!"
    )
    command_ids = fields.One2many(
        "l10n.bg.telegram.bot.command", "bot_id", string="Commands", copy=True
    )
    user_ids = fields.One2many("l10n.bg.telegram.user", "bot_id", string="Users")
    user_count = fields.Integer(compute="_compute_user_count")
    webhook_url = fields.Char(compute="_compute_webhook_url")
    webhook_state = fields.Selection(
        [("none", "Not set"), ("set", "Set")],
        default="none",
        readonly=True,
        copy=False,
    )

    @api.depends("user_ids")
    def _compute_user_count(self):
        for bot in self:
            bot.user_count = len(bot.user_ids)

    def _compute_webhook_url(self):
        for bot in self:
            bot.webhook_url = (
                urls.urljoin(bot.get_base_url(), f"{WEBHOOK_ROUTE}/{bot.id}")
                if bot.id
                else False
            )

    # --- Bot API ---------------------------------------------------------

    def _api_call(self, method, payload=None):
        """Извиква метод на Bot API и връща `result`; грешката става UserError."""
        self.ensure_one()
        token = self.sudo().token
        if not token:
            raise UserError(self.env._("The bot %s has no token.", self.name))
        try:
            response = requests.post(
                f"{API_BASE}/bot{token}/{method}",
                json=payload or {},
                timeout=API_TIMEOUT,
            )
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            # Токенът е в URL-а ⇒ не логваме изключението с URL-а, само типа
            _logger.warning("Telegram %s failed: %s", method, type(error).__name__)
            raise UserError(
                self.env._("Telegram is not reachable (%s).", method)
            ) from None
        if not data.get("ok"):
            raise UserError(
                self.env._(
                    "Telegram rejected %(method)s: %(error)s",
                    method=method,
                    error=data.get("description") or response.status_code,
                )
            )
        return data.get("result")

    def send_message(self, chat_id, text, **kwargs):
        """Изпраща текст до чат; допълнителните аргументи отиват към sendMessage."""
        self.ensure_one()
        return self._api_call(
            "sendMessage", {"chat_id": chat_id, "text": text, **kwargs}
        )

    def _profile_languages(self):
        """Двойки (код в Odoo, ISO 639-1 за Telegram) за инсталираните езици.

        Telegram приема само двубуквен `language_code`; при два езика с еднакъв
        ISO (pt_BR/pt_PT) остава първият по име.
        """
        pairs, seen = [], set()
        Lang = self.env["res.lang"]
        for code, _name in Lang.get_installed():
            iso = (Lang._lang_get(code).iso_code or code)[:2].lower()
            if iso not in seen:
                seen.add(iso)
                pairs.append((code, iso))
        return pairs

    def _default_profile_lang(self):
        """Езикът за хората, чийто език не е сред инсталираните."""
        installed = [code for code, _name in self.env["res.lang"].get_installed()]
        for code in ("en_US", self.company_id.partner_id.lang):
            if code in installed:
                return code
        return installed[0] if installed else "en_US"

    def _push_profile(self, language_code=None):
        """Описанията и командите на езика от контекста; без код — по подразбиране."""
        self.ensure_one()
        scope = {"language_code": language_code} if language_code else {}
        self._api_call(
            "setMyDescription", {"description": self.description or "", **scope}
        )
        self._api_call(
            "setMyShortDescription",
            {"short_description": self.short_description or "", **scope},
        )
        self._api_call(
            "setMyCommands",
            {
                "commands": [
                    {"command": c.command, "description": c.description}
                    for c in self.command_ids
                ],
                **scope,
            },
        )

    def action_sync_profile(self):
        """Чете името на бота и записва описанията и командите в Telegram.

        Всеки инсталиран език получава свой превод (Telegram показва на
        потребителя тези на езика на приложението му), плюс вариант по
        подразбиране за всички останали.
        """
        for bot in self:
            me = bot._api_call("getMe")
            bot.username = me.get("username")
            bot.with_context(lang=bot._default_profile_lang())._push_profile()
            for code, iso in bot._profile_languages():
                bot.with_context(lang=code)._push_profile(iso)
        return True

    def action_set_webhook(self):
        for bot in self:
            url = bot.webhook_url
            if not url.startswith("https://"):
                raise UserError(
                    self.env._(
                        "Telegram needs an HTTPS webhook; the base URL is %s.", url
                    )
                )
            bot._api_call(
                "setWebhook",
                {
                    "url": url,
                    "secret_token": bot.sudo().webhook_secret,
                    "allowed_updates": ALLOWED_UPDATES,
                    "drop_pending_updates": True,
                },
            )
            bot.webhook_state = "set"
        return True

    def action_delete_webhook(self):
        for bot in self:
            bot._api_call("deleteWebhook")
            bot.webhook_state = "none"
        return True

    def action_view_users(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Telegram Users"),
            "res_model": "l10n.bg.telegram.user",
            "view_mode": "list,form",
            "domain": [("bot_id", "=", self.id)],
            "context": {"default_bot_id": self.id},
        }

    # --- Входящи update-и -------------------------------------------------

    def _handle_update(self, update):
        """Обработва един update от webhook-а.

        Повторно доставен update (Telegram праща пак при таймаут) се игнорира
        по уникалния `update_id` за бота.
        """
        self.ensure_one()
        if not self.env["l10n.bg.telegram.update"]._register_update(self, update):
            return
        try:
            with self.env.cr.savepoint():
                self._process_update(update)
        except Exception:
            # Update-ът остава записан като получен: иначе Telegram го повтаря
            # безкрайно. Частичната работа се връща от savepoint-а, грешката е в лога.
            _logger.exception(
                "Telegram bot %s: update %s failed", self.id, update.get("update_id")
            )

    def _process_update(self, update):
        if update.get("callback_query"):
            return self._process_callback_query(update["callback_query"])
        message = update.get("message")
        if not message or not message.get("from") or message["from"].get("is_bot"):
            return
        tg_user = self.env["l10n.bg.telegram.user"]._from_telegram(self, message)
        bot, tg_user = self._in_user_language(tg_user)
        if (message.get("chat") or {}).get("type", "private") != "private":
            return bot._process_group_message(tg_user, message)
        text = (message.get("text") or "").strip()
        tg_user._log_incoming(text)
        if text.startswith("/"):
            command, _sep, args = text[1:].partition(" ")
            # „/start@ИмеНаБота“ в група — махаме суфикса
            command = command.split("@", 1)[0].lower()
            bot._dispatch_command(tg_user, command, args.strip())

    def _process_group_message(self, tg_user, message):
        """Съобщение в група, където ботът членува.

        Основата не отговаря в групи (командите и отговорите са в личния чат);
        модулите отгоре (консултациите) записват съобщенията от своите групи.
        """
        return False

    def _in_user_language(self, tg_user):
        """Ботът и потребителят в езика на клиента.

        Webhook-ът върви като публичния потребител ⇒ без това всеки отговор
        (и всеки превеждаем текст на бота) излиза на неговия език.
        """
        lang = tg_user._get_lang()
        return self.with_context(lang=lang), tg_user.with_context(lang=lang)

    def _process_callback_query(self, query):
        """Натиснат бутон под съобщение (inline keyboard).

        `data` е „<префикс>:<аргумент>“ и отива към `_callback_<префикс>`.
        Telegram чака answerCallbackQuery, иначе бутонът „върти“ ~15 секунди.
        """
        message = query.get("message") or {}
        if not message.get("chat") or query.get("from", {}).get("is_bot"):
            return
        tg_user = self.env["l10n.bg.telegram.user"]._from_telegram(
            self, {"from": query["from"], "chat": message["chat"]}
        )
        bot, tg_user = self._in_user_language(tg_user)
        prefix, _sep, arg = (query.get("data") or "").partition(":")
        handler = (
            getattr(bot, f"_callback_{prefix}", None)
            if SAFE_NAME.fullmatch(prefix)
            else None
        )
        try:
            if handler is not None:
                handler(tg_user, arg)
        finally:
            self._api_call("answerCallbackQuery", {"callback_query_id": query["id"]})

    def _dispatch_command(self, tg_user, command, args):
        """Вика `_command_<име>`; модулите отгоре добавят команди така."""
        if not SAFE_NAME.fullmatch(command):
            return self._command_unknown(tg_user, command, args)
        handler = getattr(self, f"_command_{command}", None)
        if handler is None:
            return self._command_unknown(tg_user, command, args)
        return handler(tg_user, args)

    def _command_start(self, tg_user, args):
        tg_user._ensure_partner()
        return tg_user._reply(self.welcome_message or self.env._("Welcome!"))

    def _command_help(self, tg_user, args):
        lines = [f"/{c.command} — {c.description}" for c in self.command_ids]
        return tg_user._reply("\n".join(lines) or self.env._("No commands."))

    def _command_unknown(self, tg_user, command, args):
        return tg_user._reply(
            self.env._("Unknown command /%s. Send /help for the list.", command)
        )


class L10nBgTelegramBotCommand(models.Model):
    _name = "l10n.bg.telegram.bot.command"
    _description = "Telegram Bot Command"
    _order = "sequence, id"

    bot_id = fields.Many2one("l10n.bg.telegram.bot", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    command = fields.Char(
        required=True, help="Without the slash, lowercase, e.g. buy (1-32 chars)."
    )
    description = fields.Char(required=True, translate=True)

    _command_unique = models.Constraint(
        "UNIQUE(bot_id, command)", "A command can be defined only once per bot."
    )

    @api.constrains("command")
    def _check_command(self):
        # Правилото на Telegram: 1–32 знака, само a–z, 0–9 и _
        for record in self:
            if not SAFE_NAME.fullmatch(record.command or ""):
                raise ValidationError(
                    self.env._(
                        "Command %s: use 1-32 lowercase letters, digits or underscores.",  # noqa: E501
                        record.command,
                    )
                )
