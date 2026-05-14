# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Fields whose values are safe to log. Anything else gets redacted to '***'
# to comply with myPOS AUP (no PAN/CVV/PIN in logs) and PCI-DSS guidance on
# cardholder data — even masked PAN counts as restricted data class.
_LOG_SAFE_KEYS = frozenset({
    "IPCmethod", "IPCVersion", "Status", "StatusMsg",
    "OrderID", "IPC_Trnref", "Amount", "Currency",
})


def _redact_for_log(data):
    """Return a shallow copy with non-allowlisted values masked.

    Empty values pass through (no risk + helps see which fields were absent).
    """
    return {k: (v if (not v or k in _LOG_SAFE_KEYS) else "***") for k, v in data.items()}


class MyPosController(http.Controller):
    _return_url = "/payment/mypos/ok"
    _cancel_url = "/payment/mypos/cancel"
    _notify_url = "/payment/mypos/notify"

    @http.route(_return_url, type="http", auth="public", methods=["GET", "POST"], csrf=False, save_session=False)
    def mypos_return(self, **data):
        _logger.info("myPOS return: %s", pprint.pformat(_redact_for_log(data)))
        if data:
            request.env["payment.transaction"].sudo()._handle_notification_data("mypos", data)
        return request.redirect("/payment/status")

    @http.route(_cancel_url, type="http", auth="public", methods=["GET", "POST"], csrf=False, save_session=False)
    def mypos_cancel(self, **data):
        # NB: do NOT inject Status="cancel" here — that mutation would break
        # signature verification downstream. The gateway already signs a
        # Status field on cancel callbacks; if it's absent we let
        # _process_notification_data flag the missing-signature/status error
        # instead of fabricating one.
        _logger.info("myPOS cancel: %s", pprint.pformat(_redact_for_log(data)))
        if data:
            request.env["payment.transaction"].sudo()._handle_notification_data("mypos", data)
        return request.redirect("/payment/status")

    @http.route(_notify_url, type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def mypos_notify(self, **data):
        _logger.info("myPOS notify: %s", pprint.pformat(_redact_for_log(data)))
        request.env["payment.transaction"].sudo()._handle_notification_data("mypos", data)
        return "OK"
