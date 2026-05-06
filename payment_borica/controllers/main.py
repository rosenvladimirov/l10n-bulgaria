# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BoricaController(http.Controller):
    _return_url = "/payment/borica/return"

    @http.route(_return_url, type="http", auth="public", methods=["GET", "POST"],
                csrf=False, save_session=False)
    def borica_return(self, **data):
        _logger.info("Borica return: %s", pprint.pformat(data))
        if data:
            request.env["payment.transaction"].sudo()._handle_notification_data("borica", data)
        return request.redirect("/payment/status")
