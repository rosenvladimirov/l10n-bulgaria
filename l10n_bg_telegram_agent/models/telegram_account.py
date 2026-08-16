# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""telegram.account — едно по едно за всеки слушащ listener/proxy.

Държи HMAC тайната (за валидиране на входящите /inject заявки) и
изходния endpoint на listener-а (където пращаме отговорите обратно).
Аналог на `erpnet.fp.proxy`, но за Telegram моста — нарочно отделен,
за да не влачим фискалния стек.
"""
import hashlib
import hmac
import logging
import secrets

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

# User-Agent ЗАДЪЛЖИТЕЛЕН — Cloudflare фронтва публичния Centrifugo hub и
# блокира default UA с 403 challenge page (научено при cf_subscriber/publish).
_CF_UA = "odoo-telegram-agent/2.0"


class TelegramAccount(models.Model):
    _name = "telegram.account"
    _description = "Telegram Bridge Account"

    name = fields.Char(required=True, help="Listener/proxy identifier (matches X-Tg-Proxy header).")
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [("pairing", "Pairing"), ("active", "Active"), ("archived", "Archived")],
        default="active", required=True)
    # HMAC тайна — генерира се; listener-ът я ползва за подпис на body-то.
    registry_secret = fields.Char(
        string="HMAC Secret", copy=False,
        help="Shared secret; the listener signs each inbound body with it.")
    # Изходящ endpoint на listener-а (telethon send), напр. http://host:9105/send
    send_endpoint = fields.Char(
        string="Outbound Send URL",
        help="Listener endpoint that delivers replies to Telegram "
             "(POST {chat_id, text}).")

    # ── Centrifugo consumer (v2 — вариант А, Odoo директен абонат) ──────
    # Вместо webhook от listener, Odoo сам дърпа входящите от Centrifugo hub-а
    # през history API (cron polling — Odoo-native, без дълготраен SSE).
    centrifugo_api_url = fields.Char(
        string="Centrifugo API URL",
        help="Base API, e.g. https://centrifugo.mcpworks.net/api "
             "(history endpoint = <base>/history; publish = <base>/publish).")
    centrifugo_api_key = fields.Char(string="Centrifugo API Key", copy=False)
    centrifugo_channel = fields.Char(
        string="Centrifugo Channel", help="e.g. telegram:rosen:359886100204")
    cf_offset = fields.Integer(
        string="CF stream offset", default=0, copy=False,
        help="Last consumed Centrifugo history offset (recovery cursor).")
    cf_epoch = fields.Char(string="CF stream epoch", copy=False)
    cf_poll_enabled = fields.Boolean(string="Poll Centrifugo", default=False)
    cf_last_poll = fields.Datetime(string="Last poll", readonly=True, copy=False)

    channel_ids = fields.One2many(
        "telegram.channel", "account_id", string="Bound Chats")
    channel_count = fields.Integer(compute="_compute_channel_count")

    @api.depends("channel_ids")
    def _compute_channel_count(self):
        for rec in self:
            rec.channel_count = len(rec.channel_ids)

    def action_rotate_secret(self):
        for rec in self:
            rec.registry_secret = secrets.token_hex(32)
        return True

    # ── Centrifugo history polling ──────────────────────────────────────
    def _cf_history(self):
        """POST <api>/history → връща (publications, offset, epoch) или None.

        Ползва `since` от запазения offset/epoch за инкрементално четене
        (Centrifugo force_recovery + history). Cloudflare иска UA.
        """
        self.ensure_one()
        if requests is None:
            _logger.error("telegram_agent: python 'requests' missing")
            return None
        base = (self.centrifugo_api_url or "").rstrip("/")
        if not base or not self.centrifugo_api_key or not self.centrifugo_channel:
            return None
        body = {"channel": self.centrifugo_channel, "limit": 100, "reverse": False}
        if self.cf_epoch:
            body["since"] = {"offset": self.cf_offset, "epoch": self.cf_epoch}
        try:
            resp = requests.post(
                base + "/history", json=body, timeout=15,
                headers={"X-API-Key": self.centrifugo_api_key,
                         "Content-Type": "application/json", "User-Agent": _CF_UA})
            resp.raise_for_status()
            res = (resp.json() or {}).get("result") or {}
            return (res.get("publications") or [],
                    res.get("offset", self.cf_offset), res.get("epoch", self.cf_epoch))
        except Exception as e:  # noqa: BLE001
            _logger.warning("telegram_agent: CF history failed (%s): %s",
                            self.centrifugo_channel, e)
            return None

    def _cf_poll_once(self):
        """Дърпа новите публикации и ги подава на telegram.channel._ingest."""
        self.ensure_one()
        out = self._cf_history()
        if out is None:
            return 0
        pubs, offset, epoch = out
        Channel = self.env["telegram.channel"]
        n = 0
        for pub in pubs:
            data = pub.get("data") or {}
            if not isinstance(data, dict) or data.get("chat_id") in (None, ""):
                continue
            try:
                # envelope формат, който _ingest очаква: {"data": {...}}
                Channel._ingest(self, {"data": data})
                n += 1
            except Exception:  # noqa: BLE001
                _logger.exception("telegram_agent: ingest failed for %s", data)
        # Запазваме cursor-а само ако напреднахме (idempotent при повтаряне).
        vals = {"cf_last_poll": fields.Datetime.now()}
        if offset and offset != self.cf_offset:
            vals["cf_offset"] = offset
        if epoch and epoch != self.cf_epoch:
            vals["cf_epoch"] = epoch
        self.sudo().write(vals)
        return n

    @api.model
    def _cron_poll_centrifugo(self):
        """ir.cron вход — обхожда активните акаунти с включен poll."""
        accounts = self.search([
            ("active", "=", True), ("cf_poll_enabled", "=", True),
            ("centrifugo_channel", "!=", False)])
        total = 0
        for acc in accounts:
            total += acc._cf_poll_once()
        if total:
            _logger.info("telegram_agent: Centrifugo poll ingested %s message(s)", total)
        return total

    def verify_signature(self, body: bytes, sig_hex: str) -> bool:
        """Constant-time HMAC-SHA256 проверка (същата схема като bus_inject)."""
        self.ensure_one()
        if not self.registry_secret or not sig_hex:
            return False
        expected = hmac.new(
            self.registry_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        try:
            return hmac.compare_digest(expected, sig_hex.strip())
        except (TypeError, ValueError):
            return False
