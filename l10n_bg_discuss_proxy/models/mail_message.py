# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""mail.message hook — излъчва Discuss съобщенията на наблюдаваните
потребители към Centrifugo прокси-чата, за да ги слуша външен Claude.

Огледало на Telegram моста: там Telegram→Centrifugo→Discuss; тук
Discuss→Centrifugo→Claude. „Един клиент в проксито слуша всички мои
комуникации" → ВСИЧКИ канали, в които наблюдаваният потребител е член,
отиват в ЕДИН канал `discuss:<login>`.
"""
import logging
import re

from odoo import api, models

_logger = logging.getLogger(__name__)


def _safe(token):
    """Centrifugo-safe токен (без @/./интервали/двоеточия)."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", token or "x")


def _chan(tenant, login):
    """Per-stack Centrifugo канал: ``discuss:<tenant>:<login>``.

    МЦП правило: услугите се делят per-stack. Login сам по себе си НЕ е
    глобално уникален между стакове (всеки стак има `admin`), затова tenant
    (кода на стака) го прави уникален — точно както телефонът прави telegram
    принципала уникален. Namespace-ът за Centrifugo е първата дума (`discuss`);
    останалите двоеточия са просто част от името на канала."""
    return "discuss:" + _safe(tenant) + ":" + _safe(login)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

# Cloudflare фронтва публичния Centrifugo hub и блокира default UA → 403.
_CF_UA = "odoo-discuss-proxy/1.0"


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        msgs = super().create(vals_list)
        # Мек — никога не чупим записването на съобщение заради проксито.
        try:
            msgs.sudo()._discuss_proxy_publish()
        except Exception:  # noqa: BLE001
            _logger.exception("discuss_proxy: publish failed")
        return msgs

    def _discuss_proxy_publish(self):
        ICP = self.env["ir.config_parameter"].sudo()
        base = (ICP.get_param("discuss_proxy.centrifugo_url") or "").rstrip("/")
        key = (ICP.get_param("discuss_proxy.centrifugo_api_key") or "").strip()
        if not base or not key or requests is None:
            return
        # Идентичност на стака (per-stack изолация). Default = db име.
        tenant = (ICP.get_param("discuss_proxy.tenant_code")
                  or self.env.cr.dbname or "").strip()
        # Бот-автори (отговорите на Claude през отделен бот-юзър) — НИКОГА не се
        # излъчват в никой канал → loop guard. discuss_proxy.bot_partner_ids =
        # CSV/space partner_id-та (напр. "2324"). Празно = изключено.
        bot_pids = {int(x) for x in (ICP.get_param("discuss_proxy.bot_partner_ids")
                    or "").replace(",", " ").split() if x.strip().isdigit()}
        # Наблюдавани, чиито СОБСТВЕНИ съобщения ВСЕ ПАК се излъчват (изключва
        # self-skip-а) — за да може наблюдаваният да пише от телефона и listener-ът
        # да го вижда. Loop защитата остава през bot_partner_ids (отговорите на
        # Claude са от бот-юзъра, не от наблюдавания). CSV partner_id-та.
        publish_self_pids = {int(x) for x in (ICP.get_param("discuss_proxy.publish_self_partner_ids")
                             or "").replace(",", " ").split() if x.strip().isdigit()}
        Users = self.env["res.users"].sudo()
        for m in self:
            # Само истински разговори в discuss.channel (не log notes, не др. модели).
            if m.model != "discuss.channel" or not m.res_id:
                continue
            if m.message_type not in ("comment",):
                continue
            channel = self.env["discuss.channel"].sudo().browse(m.res_id)
            if not channel.exists():
                continue
            member_pids = channel.channel_partner_ids.ids
            if not member_pids:
                continue
            # BOT guard: отговор от бот-юзър (Claude) → не излъчвай в НИКОЙ канал.
            if m.author_id and m.author_id.id in bot_pids:
                continue
            # Наблюдавани потребители, които СА в този канал.
            monitored = Users.search([
                ("claude_discuss_proxy", "=", True),
                ("partner_id", "in", member_pids),
            ])
            for u in monitored:
                # Echo guard: НЕ излъчваме собствените съобщения на наблюдавания
                # (вкл. отговорите на Claude, които се пишат като него) — иначе loop.
                if (m.author_id and u.partner_id and m.author_id.id == u.partner_id.id
                        and u.partner_id.id not in publish_self_pids):
                    continue
                self._cf_publish(base, key, _chan(tenant, u.login), {
                    "channel_id": channel.id,
                    "channel_name": channel.name or "",
                    "channel_type": channel.channel_type or "",
                    "msg_id": m.id,
                    "author_id": m.author_id.id if m.author_id else None,
                    "author": m.author_id.name if m.author_id else (m.email_from or ""),
                    "text": (m.body or "").strip(),
                    "date": m.date.isoformat() if m.date else "",
                })

    def _cf_publish(self, base, key, channel, data):
        """POST <base>/publish — same scheme като telegram_agent (UA срещу CF)."""
        try:
            resp = requests.post(
                base + "/publish",
                json={"channel": channel, "data": data},
                timeout=10,
                headers={"X-API-Key": key, "Content-Type": "application/json",
                         "User-Agent": _CF_UA},
            )
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001
            _logger.warning("discuss_proxy: CF publish to %s failed: %s", channel, e)
