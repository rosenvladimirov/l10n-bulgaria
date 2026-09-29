# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

from ..const import SALE_RESPONSE_SIGN_FIELDS

_logger = get_payment_logger(__name__)


class BoricaController(http.Controller):
    _return_url = "/payment/borica/return"

    @http.route(
        _return_url,
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def borica_return(self, **data):
        """Връщане от шлюза на Борика (BACKREF).

        `save_session=False` по същата причина като в ядрото: POST от чужд домейн
        може да дойде без бисквитката на сесията; `/payment/status` я намира после.
        """
        _logger.info(
            "handling redirection from Borica with data:\n%s", pprint.pformat(data)
        )
        if data:
            tx_sudo = (
                request.env["payment.transaction"]
                .sudo()
                ._search_by_reference("borica", data)
            )
            if tx_sudo:
                self._verify_signature(data, tx_sudo)
                tx_sudo._process("borica", data)
        return request.redirect("/payment/status")

    @staticmethod
    def _verify_signature(payment_data, tx_sudo):
        """Проверява P_SIGN на отговора с публичния сертификат на Борика.

        Без валиден подпис данните не се обработват — иначе всеки може да
        „плати“ поръчка с ръчно сглобен POST.
        """
        p_sign = payment_data.get("P_SIGN")
        if not p_sign:
            _logger.warning("Received Borica payment data with missing P_SIGN")
            raise Forbidden()
        if not tx_sudo.provider_id._borica_verify(
            payment_data, p_sign, SALE_RESPONSE_SIGN_FIELDS
        ):
            _logger.warning(
                "Received Borica payment data with invalid P_SIGN for %s",
                tx_sudo.reference,
            )
            raise Forbidden()
