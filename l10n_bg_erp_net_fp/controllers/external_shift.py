"""
HTTP controller for the standalone External Shift dashboard frontend.

Mirrors `point_of_sale.PosController.pos_web()` — a single
`request.render()` call against a QWeb template that emits a full
HTML page including `<t t-call-assets>` for the dedicated bundle.
"""

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ExternalShiftController(http.Controller):

    @http.route(
        ["/external-shift", "/external-shift/<int:shift_id>"],
        type="http", auth="user", website=False,
    )
    def external_shift_app(self, shift_id=None, **kwargs):
        """Render the External Shift dashboard shell page."""
        if not shift_id and "shift_id" in (kwargs or {}):
            try:
                shift_id = int(kwargs.get("shift_id") or 0) or None
            except (ValueError, TypeError):
                shift_id = None

        if shift_id:
            shift = request.env["l10n.bg.fiscal.shift"].browse(shift_id)
            try:
                shift.check_access_rights("read")
                shift.check_access_rule("read")
                if not shift.exists():
                    shift_id = None
            except Exception:  # noqa: BLE001
                _logger.info(
                    "User %s denied access to shift %s; rendering blank "
                    "frontend.",
                    request.env.user.login, shift_id,
                )
                shift_id = None

        company = request.env.company
        user = request.env.user
        config = {
            "shift_id": shift_id or 0,
            "user_id": user.id,
            "user_name": user.name,
            "company_id": company.id,
            "company_name": company.name,
        }
        return request.render(
            "l10n_bg_erp_net_fp.external_shift_layout",
            {
                "shift_id": shift_id or 0,
                "user_id": user.id,
                "company_id": company.id,
                "company_name": company.name,
                "config_json_safe": json.dumps(config, ensure_ascii=False),
            },
        )
