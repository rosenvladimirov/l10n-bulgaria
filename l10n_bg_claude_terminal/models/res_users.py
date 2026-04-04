# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.service.db import list_dbs

import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    # ── Terminal ──
    claude_terminal_url = fields.Char(
        "Claude Terminal URL",
        help="URL of the terminal-control-mcp web UI (e.g. http://localhost:8080)",
        default="http://localhost:8080",
    )

    # ── Odoo RPC Connector ──
    claude_odoo_url = fields.Char(
        "Odoo URL",
        help="Odoo instance URL for RPC connector (e.g. http://localhost:8069)",
        default="http://localhost:8069",
    )
    claude_odoo_db = fields.Selection(
        selection="_selection_claude_odoo_db",
        string="Database",
        help="Odoo database name for RPC connector",
    )
    claude_odoo_protocol = fields.Selection(
        [("xmlrpc", "XML-RPC"), ("jsonrpc", "JSON-RPC")],
        string="Protocol",
        default="xmlrpc",
        help="XML-RPC (Odoo 8+) or JSON-RPC (Odoo 14+)",
    )

    @api.model
    def _selection_claude_odoo_db(self):
        try:
            dbs = list_dbs(force=True)
            return [(db, db) for db in sorted(dbs)]
        except Exception:
            db = self.env.cr.dbname
            return [(db, db)]

    # ── Telegram MCP ──
    claude_telegram_api_id = fields.Char(
        "API ID",
        help="Telegram API ID from my.telegram.org",
    )
    claude_telegram_api_hash = fields.Char(
        "API Hash",
        help="Telegram API Hash from my.telegram.org",
    )
    claude_telegram_phone = fields.Char(
        "Phone",
        help="Phone number with country code (e.g. +359...)",
    )
    claude_telegram_session = fields.Char(
        "Session Name",
        help="Telegram session name (default: claude_session)",
        default="claude_session",
    )

    # ── Viber MCP ──
    claude_viber_bot_token = fields.Char(
        "Bot Token",
        help="Viber Bot API token from partners.viber.com",
    )
    claude_viber_bot_name = fields.Char(
        "Bot Name",
        help="Viber bot display name",
    )
    claude_viber_webhook_url = fields.Char(
        "Webhook URL",
        help="Public HTTPS URL for Viber webhook (e.g. https://yourdomain.com/viber/webhook)",
    )

    _CLAUDE_FIELDS = [
        "claude_terminal_url",
        "claude_odoo_url",
        "claude_odoo_db",
        "claude_odoo_protocol",
        "claude_telegram_api_id",
        "claude_telegram_api_hash",
        "claude_telegram_phone",
        "claude_telegram_session",
        "claude_viber_bot_token",
        "claude_viber_bot_name",
        "claude_viber_webhook_url",
    ]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + self._CLAUDE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + self._CLAUDE_FIELDS

    @api.model
    def get_claude_terminal_url(self):
        """RPC: return current user's terminal URL."""
        return self.env.user.claude_terminal_url or ""

    @api.model
    def notify_claude_refresh(self, payload=None):
        """Send a bus notification to refresh the user's browser view.

        Called by the MCP server (odoo_refresh tool) after creating/updating
        records so the Odoo tab auto-reloads.
        """
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "claude_terminal/refresh",
            payload or {},
        )
        return True

    @api.model
    def notify_claude_refresh_field(self, payload=None):
        """Live field-level refresh: Claude wrote specific fields on a record.

        The MCP server calls this after odoo_write() so the user's open form
        view can flash and update the specific fields that Claude changed.

        Payload format:
            {
                "kind": "field",
                "model": "sale.order",
                "res_ids": [123],
                "values": {"partner_id": 5, "note": "..."},
                "sessions": [{session_id, model, res_id, view_type}, ...]
            }
        """
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "claude_terminal/refresh_field",
            payload or {},
        )
        return True

    @api.model
    def notify_claude_refresh_list(self, payload=None):
        """Live list refresh: Claude created a new record.

        Called after odoo_create() so open list views can highlight the new
        row without a full reload.

        Payload format:
            {
                "kind": "list",
                "model": "sale.order",
                "res_ids": [456],
                "values": {...},
                "sessions": [...]
            }
        """
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "claude_terminal/refresh_list",
            payload or {},
        )
        return True

    @api.model
    def get_claude_mcp_config(self):
        """RPC: return current user's full MCP configuration for the terminal."""
        user = self.env.user
        return {
            "terminal_url": user.claude_terminal_url or "",
            "odoo": {
                "url": user.claude_odoo_url or "",
                "db": user.claude_odoo_db or self.env.cr.dbname,
                "username": user.login,
                "protocol": user.claude_odoo_protocol or "xmlrpc",
            },
            "telegram": {
                "api_id": user.claude_telegram_api_id or "",
                "api_hash": user.claude_telegram_api_hash or "",
                "phone": user.claude_telegram_phone or "",
                "session_name": user.claude_telegram_session or "",
            },
            "viber": {
                "bot_token": user.claude_viber_bot_token or "",
                "bot_name": user.claude_viber_bot_name or "",
                "webhook_url": user.claude_viber_webhook_url or "",
            },
        }
