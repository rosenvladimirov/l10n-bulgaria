# Telegram Bot: Consultations

`/consult topic @colleague …` creates a request on the client's prepaid hours (a confirmed
order line in an hour unit with `remaining_hours` left). The consultation manager set on the
bot gets Approve/Reject buttons in Telegram (only they can use them); the same actions exist
in the Odoo form. After approval, the MCP tool `telegram_create_group` reads
`l10n_bg_consult_payload()`, creates the group from the human's account and calls
`l10n_bg_set_group(chat_id, invite_link)`; the bot sends the invitation to the client.

**Module:** `l10n_bg_telegram_consult` | **Version:** 19.0.1.2.0 | **License:** LGPL-3
