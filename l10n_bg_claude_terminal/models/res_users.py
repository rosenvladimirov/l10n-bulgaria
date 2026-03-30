# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    claude_terminal_url = fields.Char(
        "Claude Terminal URL",
        help="URL of the terminal-control-mcp web UI (e.g. http://localhost:8080)",
        default="http://localhost:8080",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["claude_terminal_url"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["claude_terminal_url"]

    @api.model
    def get_claude_terminal_url(self):
        """RPC: return current user's terminal URL (no uid needed)."""
        return self.env.user.claude_terminal_url or ""
