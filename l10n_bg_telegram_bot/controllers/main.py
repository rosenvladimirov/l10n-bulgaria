# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import hmac
import json
import logging

from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.http import request

from ..models.l10n_bg_telegram_bot import WEBHOOK_ROUTE

_logger = logging.getLogger(__name__)


class L10nBgTelegramWebhook(http.Controller):
    @http.route(
        f"{WEBHOOK_ROUTE}/<int:bot_id>",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def webhook(self, bot_id, **_kwargs):
        bot = request.env["l10n.bg.telegram.bot"].sudo().browse(bot_id).exists()
        if not bot or not bot.active:
            raise NotFound()
        received = request.httprequest.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )
        if not bot.webhook_secret or not hmac.compare_digest(
            received.encode(), bot.webhook_secret.encode()
        ):
            _logger.warning("Telegram webhook for bot %s: bad secret token", bot_id)
            raise Forbidden()
        try:
            update = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError:
            return request.make_response("bad json", status=400)
        bot._handle_update(update)
        return request.make_response("ok")
