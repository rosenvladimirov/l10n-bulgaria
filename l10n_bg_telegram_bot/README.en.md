# Telegram Bot (base)

A @BotFather bot driven by Odoo — the base for selling consultations over Telegram.

**Module:** `l10n_bg_telegram_bot` | **Version:** 19.0.1.2.0 | **License:** LGPL-3 | **Depends:** `mail`

- `l10n.bg.telegram.bot`: token, webhook secret, descriptions, commands; *Sync with Telegram*
  (getMe, setMyDescription, setMyShortDescription, setMyCommands) and *Set Webhook*
  (setWebhook with `secret_token`, HTTPS only).
- Webhook `/l10n_bg_telegram/webhook/<id>`: requires the `X-Telegram-Bot-Api-Secret-Token`
  header (403 otherwise); redelivered updates are ignored by `update_id`; a failing handler is
  rolled back to a savepoint and Telegram still gets 200 so it does not retry forever.
- `l10n.bg.telegram.user`: Telegram id (string — over 32 bits), private chat, contact created on
  `/start`; incoming messages and replies are kept in the chatter.
- Commands `/start`, `/help`; modules on top add `_command_<name>` methods to the bot.

Menu: the Telegram app (administrators only).

Replies follow each client's language (contact language, else the Telegram app language
matched to installed languages, else English); *Sync with Telegram* pushes descriptions and
commands per installed language (`language_code`) plus a default.
