# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Claude Terminal (Chatter & List View)",
    "version": "16.0.1.16.0",
    "category": "Technical",
    "summary": "Claude Code terminal in chatter, list & kanban view — connects to MCP Docker stack",
    "author": "Rosen Vladimirov, BL Consulting, Odoo Community Association (OCA)",
    "maintainers": ["rosen-vladimirov"],
    "website": "https://github.com/nicePrintBulgaria/l10n-bulgaria",
    "license": "AGPL-3",
    "depends": ["mail", "web", "bus", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_claude_terminal/static/src/scss/terminal.scss",
            "l10n_bg_claude_terminal/static/src/scss/terminal_live_refresh.scss",
            "l10n_bg_claude_terminal/static/src/js/terminal_refresh_service.js",
            "l10n_bg_claude_terminal/static/src/js/terminal_live_refresh.js",
            "l10n_bg_claude_terminal/static/src/js/terminal_utils.js",
            "l10n_bg_claude_terminal/static/src/js/terminal_chatter.js",
            "l10n_bg_claude_terminal/static/src/xml/terminal_chatter.xml",
            "l10n_bg_claude_terminal/static/src/js/terminal_listview.js",
            "l10n_bg_claude_terminal/static/src/xml/terminal_listview.xml",
            "l10n_bg_claude_terminal/static/src/js/terminal_kanbanview.js",
            "l10n_bg_claude_terminal/static/src/xml/terminal_kanbanview.xml",
        ],
    },
    "installable": True,
    "application": False,
}
