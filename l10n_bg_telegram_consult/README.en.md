# Telegram Bot: Consultations

`/consult topic @colleague …` creates a request on the client's prepaid hours (a confirmed
order line in an hour unit with `remaining_hours` left). The consultation manager set on the
bot gets Approve/Reject buttons in Telegram (only they can use them); the same actions exist
in the Odoo form. After approval, the MCP tool `telegram_create_group` reads
`l10n_bg_consult_payload()`, creates the group from the human's account and calls
`l10n_bg_set_group(chat_id, invite_link)`; the bot sends the invitation to the client.

**Module:** `l10n_bg_telegram_consult` | **Version:** 19.0.1.3.0 | **License:** LGPL-3

**Duty.** `tools/tg_duty_consult.py watch S00001` puts Claude on duty: group messages reach
Odoo through the bot, Claude writes drafts that go to the manager for approval (only approved
replies reach the group), time runs on the prepaid hours and is logged on the task in 15-minute
steps; a cron warns 15 minutes before the end and stops the duty when the hours are used up.
