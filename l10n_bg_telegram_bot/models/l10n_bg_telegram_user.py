# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class L10nBgTelegramUser(models.Model):
    _name = "l10n.bg.telegram.user"
    _description = "Telegram User"
    _inherit = "mail.thread"
    _rec_name = "display_label"

    bot_id = fields.Many2one(
        "l10n.bg.telegram.bot", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="bot_id.company_id", store=True)
    # Telegram id-тата са до 52 бита — Integer в Odoo е 32-битов ⇒ низ
    telegram_id = fields.Char(string="Telegram ID", required=True, readonly=True)
    chat_id = fields.Char(
        readonly=True, help="Private chat with the bot, used for replies."
    )
    username = fields.Char(readonly=True)
    first_name = fields.Char(readonly=True)
    last_name = fields.Char(readonly=True)
    language_code = fields.Char(readonly=True)
    partner_id = fields.Many2one("res.partner", string="Contact", tracking=True)
    display_label = fields.Char(compute="_compute_display_label", store=True)

    _telegram_id_unique = models.Constraint(
        "UNIQUE(bot_id, telegram_id)", "A Telegram user is registered once per bot."
    )

    @api.depends("username", "first_name", "last_name", "telegram_id")
    def _compute_display_label(self):
        for user in self:
            name = " ".join(filter(None, [user.first_name, user.last_name]))
            if user.username:
                name = f"{name} (@{user.username})" if name else f"@{user.username}"
            user.display_label = name or user.telegram_id

    @api.model
    def _from_telegram(self, bot, message):
        """Намира или създава потребителя по `from` на съобщението; обновява данните."""
        sender = message["from"]
        values = {
            "chat_id": str(message["chat"]["id"]),
            "username": sender.get("username"),
            "first_name": sender.get("first_name"),
            "last_name": sender.get("last_name"),
            "language_code": sender.get("language_code"),
        }
        user = self.search(
            [("bot_id", "=", bot.id), ("telegram_id", "=", str(sender["id"]))], limit=1
        )
        if user:
            # Пишем само промененото — иначе всяко съобщение прави запис
            changed = {k: v for k, v in values.items() if user[k] != (v or False)}
            if changed:
                user.write(changed)
            return user
        return self.create(
            {"bot_id": bot.id, "telegram_id": str(sender["id"]), **values}
        )

    def _ensure_partner(self):
        """Връзва партньор при /start; съществуващата връзка не се пипа."""
        for user in self.filtered(lambda u: not u.partner_id):
            name = " ".join(filter(None, [user.first_name, user.last_name]))
            user.partner_id = self.env["res.partner"].create(
                {
                    "name": name or user.username or user.telegram_id,
                    "company_id": user.company_id.id,
                    "comment": f"Telegram @{user.username}" if user.username else False,
                }
            )
        return self.partner_id

    def _log_incoming(self, text):
        self.ensure_one()
        self.message_post(body=text or self.env._("(non-text message)"))

    def _reply(self, text, **kwargs):
        """Отговаря в личния чат и записва отговора в историята."""
        self.ensure_one()
        result = self.bot_id.send_message(self.chat_id, text, **kwargs)
        self.message_post(body=text, subtype_xmlid="mail.mt_note")
        return result
