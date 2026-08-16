# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""telegram.channel — мост между един Telegram чат и една Discuss сесия.

Всеки запис връзва:
    Telegram chat_id  ↔  discuss.channel (вътрешния чат = контекстната сесия)

Поток (вж. README):
    listener → POST /telegram_agent/inbound (HMAC)
             → telegram.channel._ingest(envelope)
                 ├─ message_post в discuss.channel          (историята = контекст)
                 ├─ bus.bus._sendone(TG канал, payload)      (live сигнал/toast)
                 └─ ако mode=auto → _generate_and_reply()
                        → _post_reply(text)
                            ├─ message_post (bot) в discuss.channel
                            └─ _send_to_telegram(text)  → listener /send
"""
import json
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

# Канал в bus.bus за live сигнал към UI/терминала (toast / „ново съобщение").
TELEGRAM_INBOUND_CHANNEL = "telegram_agent_inbound"


class TelegramChannel(models.Model):
    _name = "telegram.channel"
    _description = "Telegram ↔ Discuss Session"
    _order = "last_message_date desc, id desc"

    account_id = fields.Many2one(
        "telegram.account", required=True, ondelete="cascade", index=True)
    chat_id = fields.Char(
        required=True, index=True,
        help="Telegram chat id (positive for users, -100... for groups).")
    title = fields.Char(help="Human label for the Telegram chat.")
    partner_id = fields.Many2one(
        "res.partner", help="Telegram counterpart as an Odoo contact (optional).")
    discuss_channel_id = fields.Many2one(
        "discuss.channel", string="Discuss Session", ondelete="set null",
        help="Internal chat carrying the conversation history (= context).")
    mode = fields.Selection(
        [("auto", "Auto (AI replies)"),
         ("advisory", "Advisory (AI drafts, human sends)"),
         ("notify", "Notify only")],
        default="notify", required=True)
    enabled = fields.Boolean(default=True)
    persona = fields.Text(help="Scenario / persona for the AI responder.")
    last_message_date = fields.Datetime(readonly=True)

    _sql_constraints = [
        ("uniq_account_chat", "unique(account_id, chat_id)",
         "This chat is already bound for that account."),
    ]

    # ── lookup / provisioning ──────────────────────────────────────────
    @api.model
    def _find_or_create(self, account, chat_id, title=None):
        """Намира връзката по (account, chat_id) или я създава заедно с
        новата discuss.channel сесия."""
        chat_id = str(chat_id)
        rec = self.search([
            ("account_id", "=", account.id), ("chat_id", "=", chat_id)], limit=1)
        if rec:
            if title and not rec.title:
                rec.title = title
            return rec
        rec = self.create({
            "account_id": account.id, "chat_id": chat_id, "title": title or "",
        })
        rec._ensure_discuss_channel()
        return rec

    def _ensure_discuss_channel(self):
        """Гарантира, че има свързана discuss.channel (вътрешния чат)."""
        Channel = self.env["discuss.channel"].sudo()
        for rec in self:
            if rec.discuss_channel_id:
                continue
            name = "TG: %s" % (rec.title or rec.chat_id)
            rec.discuss_channel_id = Channel.create({
                "name": name,
                "channel_type": "channel",
                # Само вътрешни потребители; AI отговаря като OdooBot.
            }).id
        return True

    # ── inbound ────────────────────────────────────────────────────────
    @api.model
    def _ingest(self, account, envelope):
        """Входна точка от controller-а. envelope.data = {chat_id, sender,
        sender_id, text, media, msg_id, ts}."""
        data = envelope.get("data") or {}
        chat_id = data.get("chat_id")
        if chat_id in (None, ""):
            return False
        rec = self._find_or_create(account, chat_id, data.get("sender"))
        rec._post_incoming(data)
        # Live сигнал по bus.bus (toast / „ново съобщение") — мек, не чупи нищо.
        try:
            self.env["bus.bus"]._sendone(
                TELEGRAM_INBOUND_CHANNEL, TELEGRAM_INBOUND_CHANNEL, {
                    "channel_id": rec.id,
                    "discuss_channel_id": rec.discuss_channel_id.id,
                    "chat_id": rec.chat_id,
                    "sender": data.get("sender"),
                    "text": data.get("text"),
                })
        except Exception:  # noqa: BLE001
            _logger.exception("telegram_agent: bus signal failed")
        if rec.enabled and rec.mode == "auto":
            rec._generate_and_reply(data)
        return rec.id

    def _post_incoming(self, data):
        """Записва входящото в discuss.channel (= историята/контекста)."""
        self.ensure_one()
        self._ensure_discuss_channel()
        sender = data.get("sender") or self.chat_id
        text = data.get("text") or ("[media]" if data.get("media") else "")
        body = "<b>%s:</b> %s" % (sender, text)
        self.discuss_channel_id.sudo().message_post(
            body=body,
            author_id=self.partner_id.id or None,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.last_message_date = fields.Datetime.now()

    # ── AI responder (плъг точка към claude_terminal) ──────────────────
    def _generate_and_reply(self, data):
        """Генерира отговор и го праща. AI слоят е МЕК: ползва
        l10n_bg_claude_terminal (Qdrant + Anthropic), ако е наличен.
        Без него методът е no-op (логва), за да е модулът самостоятелно
        инсталируем за преглед."""
        self.ensure_one()
        text = self._call_llm(data)
        if not text:
            _logger.info(
                "telegram_agent: no AI reply produced for chat %s "
                "(claude_terminal not wired?)", self.chat_id)
            return False
        return self._post_reply(text)

    def _build_context(self, data, limit=20):
        """Краткосрочен контекст = последните съобщения от discuss.channel.
        Дългосрочен = Qdrant top-k (ако ai.qdrant.client е наличен) — TODO в
        runner фазата."""
        self.ensure_one()
        msgs = self.discuss_channel_id.sudo().message_ids[:limit]
        history = [{
            "author": m.author_id.name or "system",
            "body": (m.body or "").strip(),
        } for m in reversed(msgs)]
        # TODO(claude_terminal): qdrant top-k semantic recall върху persona/chat.
        return {"persona": self.persona or "", "history": history,
                "incoming": data.get("text") or ""}

    def _call_llm(self, data):
        """Фаза 3 — реален Anthropic отговор тип търговец.

        Ползва company Anthropic ключа (от l10n_bg_claude_terminal:
        res.company.claude_anthropic_api_key). Без ключ/requests → '' (no-op,
        самостоятелен режим за преглед). persona = system; кратък контекст +
        входящото отиват като user съобщение (избягва role-alternation капани).
        Моделът и max_tokens са конфигурируеми през ir.config_parameter.
        """
        self.ensure_one()
        if requests is None:
            return ""
        key = (self.env.company.sudo().claude_anthropic_api_key or "").strip() \
            if "claude_anthropic_api_key" in self.env.company._fields else ""
        if not key:
            _logger.info("telegram_agent: no Anthropic key (claude_terminal) — "
                         "AI responder is a no-op for chat %s", self.chat_id)
            return ""
        ctx = self._build_context(data)
        Param = self.env["ir.config_parameter"].sudo()
        model = Param.get_param("telegram_agent.ai_model", "claude-sonnet-4-6")
        max_tokens = int(Param.get_param("telegram_agent.ai_max_tokens", "1024"))
        system = (ctx.get("persona") or
                  "Ти си учтив търговски асистент. Отговаряй кратко, ясно и "
                  "по същество на езика на събеседника. Представяй се като Клаудчо.")
        # Краткосрочният контекст влиза в system-а (стабилно, без alternation).
        hist = ctx.get("history") or []
        if hist:
            lines = ["%s: %s" % (h.get("author", "?"), h.get("body", "")) for h in hist[-12:]]
            system += "\n\nПоследни съобщения в разговора:\n" + "\n".join(lines)
        incoming = ctx.get("incoming") or (data.get("text") or "")
        if not incoming.strip():
            return ""
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": model, "max_tokens": max_tokens, "system": system,
                      "messages": [{"role": "user", "content": incoming}]},
                timeout=40)
            resp.raise_for_status()
            blocks = (resp.json() or {}).get("content") or []
            return "".join(b.get("text", "") for b in blocks
                           if b.get("type") == "text").strip()
        except Exception as e:  # noqa: BLE001
            _logger.warning("telegram_agent: Anthropic call failed for %s: %s",
                            self.chat_id, e)
            return ""

    # ── outbound ───────────────────────────────────────────────────────
    def _post_reply(self, text):
        """Записва отговора в discuss.channel (като бот) и го праща в Telegram."""
        self.ensure_one()
        self._ensure_discuss_channel()
        self.discuss_channel_id.sudo().message_post(
            body=text, message_type="comment", subtype_xmlid="mail.mt_comment")
        self._send_to_telegram(text)
        self.last_message_date = fields.Datetime.now()
        return True

    def _send_to_telegram(self, text):
        """POST към listener-а → telethon доставя в Telegram."""
        self.ensure_one()
        url = self.account_id.send_endpoint
        if not url:
            _logger.warning("telegram_agent: no send_endpoint on account %s",
                            self.account_id.name)
            return False
        if requests is None:
            _logger.error("telegram_agent: python 'requests' missing")
            return False
        try:
            resp = requests.post(url, json={"chat_id": self.chat_id, "text": text},
                                 timeout=10)
            resp.raise_for_status()
            return True
        except Exception:  # noqa: BLE001
            _logger.exception("telegram_agent: send to %s failed", url)
            return False

    # ── UI helpers ──────────────────────────────────────────────────────
    def action_open_discuss(self):
        self.ensure_one()
        self._ensure_discuss_channel()
        return {
            "type": "ir.actions.act_window",
            "res_model": "discuss.channel",
            "res_id": self.discuss_channel_id.id,
            "view_mode": "form",
        }
