# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MyPosController(http.Controller):
    _return_url = "/payment/mypos/ok"
    _cancel_url = "/payment/mypos/cancel"
    _notify_url = "/payment/mypos/notify"

    @http.route(_return_url, type="http", auth="public", methods=["GET", "POST"], csrf=False, save_session=False)
    def mypos_return(self, **data):
        _logger.info("myPOS return: %s", pprint.pformat(data))
        if data:
            request.env["payment.transaction"].sudo()._handle_notification_data("mypos", data)
        return request.redirect("/payment/status")

    @http.route(_cancel_url, type="http", auth="public", methods=["GET", "POST"], csrf=False, save_session=False)
    def mypos_cancel(self, **data):
        _logger.info("myPOS cancel: %s", pprint.pformat(data))
        if data:
            data["Status"] = "cancel"
            request.env["payment.transaction"].sudo()._handle_notification_data("mypos", data)
        return request.redirect("/payment/status")

    @http.route(_notify_url, type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def mypos_notify(self, **data):
        _logger.info("myPOS notify: %s", pprint.pformat(data))
        request.env["payment.transaction"].sudo()._handle_notification_data("mypos", data)
        return "OK"
