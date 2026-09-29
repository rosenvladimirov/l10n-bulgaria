# Telegram Bot: Sales

Sell consultations from the Telegram bot and take the payment in the eCommerce shop.

**Module:** `l10n_bg_telegram_bot_sale` | **Version:** 19.0.1.0.0 | **License:** LGPL-3

- `/buy` — package buttons; a pressed package creates a shop order (partner from `/start`,
  salesperson and team from the website) and replies with a *Pay* button.
- *Pay* opens `/l10n_bg_telegram/pay/<order>/<access_token>`, which puts the order into the
  session cart and redirects to `/shop/checkout` — the standard shop flow from there on.
- `/voucher CODE` — `sale_loyalty` code on the last unpaid order.
- `/balance` — prepaid hours left and eWallet balances.
- `/orders` — last 5 orders with *Pay* buttons for the unpaid ones.

Configure the website and packages on the bot's *Sales* tab; add the commands on *Commands*.
