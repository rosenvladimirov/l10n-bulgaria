# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Telegram Agent — Discuss bridge",
    "version": "19.0.2.0.0",
    "summary": "Bridge Telegram chats into Odoo Discuss — v2: Centrifugo "
               "consumer (variant A) + Anthropic merchant AI responder (auto mode).",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/rosenvladimirov",
    "license": "AGPL-3",
    "category": "Discuss",
    "depends": [
        "mail",      # discuss.channel = вътрешния чат / контекстна сесия
        "bus",       # bus.bus инжекция (websocket доставка)
    ],
    # Меки интеграции (НЕ са твърди depends — модулът работи и без тях):
    #   * l10n_bg_claude_terminal → ai.qdrant.client + Anthropic ключ (AI отговор)
    #   * l10n_bg_live_refresh    → toast/live сигнал при ново съобщение
    "external_dependencies": {"python": []},
    "data": [
        "security/telegram_agent_groups.xml",
        "security/ir.model.access.csv",
        "data/telegram_agent_cron.xml",
        "views/telegram_account_views.xml",
        "views/telegram_channel_views.xml",
        "views/telegram_agent_menus.xml",
    ],
    "installable": True,
    "application": False,
}
