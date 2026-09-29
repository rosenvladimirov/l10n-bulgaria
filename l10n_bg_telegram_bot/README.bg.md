# Telegram бот (основа)

Бот от @BotFather, управляван от Odoo. Основа за продажбата на консултации през Telegram
(`telegram-consult-bot`, ADR 0001–0005).

**Модул:** `l10n_bg_telegram_bot` | **Версия:** 19.0.1.0.0 | **Лиценз:** LGPL-3 | **Зависи от:** `mail`

## Какво прави

- `l10n.bg.telegram.bot` — токен, таен ключ на webhook-а, описания, команди. Бутоните
  „Синхронизирай с Telegram“ (getMe, setMyDescription, setMyShortDescription, setMyCommands)
  и „Задай webhook“ (setWebhook с `secret_token`; само HTTPS).
- Webhook `/l10n_bg_telegram/webhook/<id>` — приема update само с правилната заглавка
  `X-Telegram-Bot-Api-Secret-Token` (иначе 403); повторно доставен update се игнорира
  (`l10n.bg.telegram.update`, уникален `update_id`); грешка в обработката се връща със
  savepoint, а Telegram получава 200, за да не повтаря.
- `l10n.bg.telegram.user` — кой пише (Telegram id е низ: над 32 бита), личният чат, контактът
  (`res.partner` се създава при `/start`); входящите съобщения и отговорите са в историята.
- Команди: `/start`, `/help`; модулите отгоре добавят `_command_<име>` към бота.

## Достъп

Менюто е в Настройки → Технически → Telegram, само за администратора.

## Настройка

1. @BotFather → `/newbot` → токенът в полето „Токен на бота“.
2. „Синхронизирай с Telegram“, после „Задай webhook“ (`web.base.url` трябва да е HTTPS).
