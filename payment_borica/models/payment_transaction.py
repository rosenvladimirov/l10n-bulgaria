# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import re
from collections import OrderedDict
from datetime import datetime, timezone

from odoo import _, models
from odoo.exceptions import ValidationError

from .payment_provider import SALE_RESPONSE_SIGN_FIELDS, SALE_SIGN_FIELDS

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "borica":
            return res

        provider = self.provider_id
        order_id = self._borica_order_id()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        nonce = provider._borica_nonce()

        signing_values = OrderedDict(
            [
                ("TERMINAL", provider.borica_terminal or ""),
                ("TRTYPE", "1"),
                ("AMOUNT", "%.2f" % self.amount),
                ("CURRENCY", self.currency_id.name),
                ("ORDER", order_id),
                ("TIMESTAMP", timestamp),
                ("NONCE", nonce),
                # RFU is signed (single literal '-') but never sent over the wire.
                ("RFU", None),
            ]
        )

        post_values = OrderedDict(
            [
                ("TERMINAL", provider.borica_terminal),
                ("TRTYPE", "1"),
                ("AMOUNT", signing_values["AMOUNT"]),
                ("CURRENCY", signing_values["CURRENCY"]),
                ("ORDER", order_id),
                ("DESC", self.reference[:50]),
                ("MERCHANT", provider.borica_merchant),
                ("MERCH_NAME", (provider.borica_merch_name or "")[:80]),
                ("MERCH_URL", provider.borica_merch_url or ""),
                ("EMAIL", (self.partner_email or provider.borica_email or "")[:80]),
                ("COUNTRY", provider.borica_country or "BG"),
                ("MERCH_GMT", provider.borica_merch_gmt or "+02"),
                ("LANG", (self.partner_lang or provider.borica_lang or "EN")[:2].upper()),
                ("ADDENDUM", "AD,TD"),
                ("AD.CUST_BOR_ORDER_ID", order_id),
                ("TIMESTAMP", timestamp),
                ("NONCE", nonce),
                ("BACKREF", self._borica_get_return_url()),
            ]
        )
        post_values["P_SIGN"] = provider._borica_sign(signing_values, SALE_SIGN_FIELDS)
        return {
            "api_url": provider._borica_get_api_url(),
            "fields": list(post_values.items()),
        }

    def _borica_order_id(self):
        """Borica ORDER must be digits-only, max 6 chars per spec."""
        self.ensure_one()
        digits = re.sub(r"\D", "", self.reference)
        return (digits or str(self.id)).rjust(6, "0")[-6:]

    def _borica_get_return_url(self):
        self.ensure_one()
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return f"{base}/payment/borica/return"

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "borica" or len(tx) == 1:
            return tx
        order = notification_data.get("ORDER")
        if not order:
            raise ValidationError(_("Borica: missing ORDER in notification"))
        tx = self.search(
            [("provider_code", "=", "borica")]
        ).filtered(lambda t: t._borica_order_id() == order.lstrip("0").rjust(6, "0"))
        if not tx:
            raise ValidationError(
                _("Borica: no transaction found for ORDER=%s") % order
            )
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != "borica":
            return

        p_sign = notification_data.get("P_SIGN")
        if not p_sign:
            self._set_error(_("Borica: missing P_SIGN in response"))
            return
        if not self.provider_id._borica_verify(
            notification_data, p_sign, SALE_RESPONSE_SIGN_FIELDS
        ):
            _logger.warning("Borica: invalid P_SIGN on response for %s", self.reference)
            self._set_error(_("Borica: invalid response signature"))
            return

        action = notification_data.get("ACTION")
        rc = notification_data.get("RC")
        # ACTION=0 RC=00 → approved
        # ACTION=2       → declined by issuer
        # ACTION=3       → SCA / authentication step in progress
        # ACTION=1       → reject (form/network)
        if action == "0" and rc == "00":
            self._set_done()
        elif action == "3":
            self._set_pending()
        elif action in ("1", "2"):
            self._set_canceled()
        else:
            self._set_error(_("Borica: unknown ACTION=%s RC=%s") % (action, rc))
