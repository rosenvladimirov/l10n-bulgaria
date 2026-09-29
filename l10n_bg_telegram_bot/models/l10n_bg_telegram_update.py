# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class L10nBgTelegramUpdate(models.Model):
    _name = "l10n.bg.telegram.update"
    _description = "Telegram Update (deduplication)"
    _log_access = False

    bot_id = fields.Many2one("l10n.bg.telegram.bot", required=True, ondelete="cascade")
    update_id = fields.Char(required=True)
    received = fields.Datetime(default=fields.Datetime.now)

    _update_unique = models.Constraint(
        "UNIQUE(bot_id, update_id)", "An update is processed only once."
    )

    @api.model
    def _register_update(self, bot, update):
        """Записва update_id; връща False, ако вече е обработен.

        Проверката е с SELECT ... и уникален индекс като пазач при състезание
        на две доставки едновременно.
        """
        update_id = str(update.get("update_id", ""))
        if not update_id:
            return False
        if self.search_count([("bot_id", "=", bot.id), ("update_id", "=", update_id)]):
            return False
        self.create({"bot_id": bot.id, "update_id": update_id})
        return True
