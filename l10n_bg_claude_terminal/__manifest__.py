# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Claude Terminal (Chatter)",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Claude Code terminal panel in chatter — connects to MCP Docker stack",
    "author": "Rosen Vladimirov, BL Consulting, Odoo Community Association (OCA)",
    "maintainers": ["rosen-vladimirov"],
    "website": "https://github.com/nicePrintBulgaria/l10n-bulgaria",
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_claude_terminal/static/src/scss/terminal.scss",
            "l10n_bg_claude_terminal/static/src/js/terminal_chatter.js",
            "l10n_bg_claude_terminal/static/src/xml/terminal_chatter.xml",
        ],
    },
    "installable": True,
    "application": False,
}
