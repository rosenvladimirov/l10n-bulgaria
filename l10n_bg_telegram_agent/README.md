# l10n_bg_telegram_agent — Telegram ↔ Odoo Discuss bridge

Свързва Telegram чатове с Odoo Discuss **по bus.bus**, като всеки чат има
собствена `discuss.channel` сесия (историята ѝ = контекстът). Не дублира
mail.thread модел — язди родния Discuss + bus.

## Архитектура

```
listener (docker, telethon)
   │  на ново съобщение:
   │   POST /telegram_agent/inbound   (HMAC: X-Tg-Signature, X-Tg-Proxy)
   ▼
controllers/inbound.py  ── валидира HMAC спрямо telegram.account.registry_secret
   │
   ▼
telegram.channel._ingest(account, envelope)
   ├─ _find_or_create        (chat_id ↔ discuss.channel; авто-създава сесията)
   ├─ _post_incoming         → message_post в discuss.channel (= контекст/история)
   ├─ bus.bus._sendone(TELEGRAM_INBOUND_CHANNEL, …)   (live сигнал/toast)
   └─ ако mode=auto → _generate_and_reply()
          → _call_llm()  (Anthropic+Qdrant през claude_terminal — Фаза 3)
          → _post_reply(text)
               ├─ message_post (bot) в discuss.channel
               └─ _send_to_telegram(text) → POST account.send_endpoint  → telethon
```

Discuss сам broadcast-ва по bus.bus, така че Claude Terminal / Discuss UI
получават съобщенията в реално време — „вътрешния чат пак по бус шината".

## Модели
- **telegram.account** — listener/proxy: HMAC тайна (`registry_secret`,
  `action_rotate_secret`), изходящ `send_endpoint`. Аналог на `erpnet.fp.proxy`.
- **telegram.channel** — 1 ред = 1 Telegram чат ↔ 1 `discuss.channel`. Полета:
  `chat_id`, `partner_id`, `mode` (auto/advisory/notify), `enabled`, `persona`.

## Статус по фази
- ✅ **Фаза 1–2 (този модул):** inbound HMAC controller, account+channel модели,
  авто-създаване на discuss.channel, message_post на входящи, bus сигнал,
  outbound `_send_to_telegram`, security, UI (Sessions/Accounts менюта).
- ⏳ **Фаза 3 (runner, плъг точка `_call_llm`):** реалният Anthropic +
  Qdrant top-k контекст през `l10n_bg_claude_terminal`. Сега `_call_llm`
  връща '' ако claude_terminal липсва → модулът е самостоятелно инсталируем
  за преглед, без да отговаря автоматично.
- ⏳ **Фаза 4:** одобрение (advisory), конфиденциалност-guard, enroll wizard.

## Промени извън Odoo (НЕ в този модул, предстоят)
Listener-ът (`~/odoo-claude-connections/tg_listener/`) трябва да получи:
1. изходящ `POST /send {chat_id,text}` endpoint (telethon изпраща);
2. на ново съобщение → подписан `POST /telegram_agent/inbound`.

## Меки зависимости
Работи с твърди depends само `mail`, `bus`. Ако са инсталирани
`l10n_bg_claude_terminal` (Qdrant/Anthropic) и `l10n_bg_live_refresh` (toast),
се ползват автоматично; иначе се деградира тихо.
