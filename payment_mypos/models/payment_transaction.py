# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
from collections import OrderedDict

from odoo import _, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "mypos":
            return res

        provider = self.provider_id
        payload = self._mypos_build_purchase_payload()
        signature = provider._mypos_sign(payload)
        return {
            "api_url": provider._mypos_get_api_url(),
            "fields": list(payload.items()),
            "signature": signature,
        }

    def _mypos_build_purchase_payload(self):
        """Build the ordered dict of POST fields signed by myPOS.

        Field order MUST match what is signed — myPOS concatenates values
        with '-' in the same order they are sent. Any reordering breaks
        signature verification on the gateway side.
        """
        self.ensure_one()
        provider = self.provider_id
        return OrderedDict(
            [
                ("IPCmethod", "IPCPurchase"),
                ("IPCVersion", "1.4"),
                ("IPCLanguage", (self.partner_lang or "en")[:2].lower()),
                ("SID", provider.mypos_sid or ""),
                ("WalletNumber", provider.mypos_wallet or ""),
                ("KeyIndex", str(provider.mypos_key_index or 1)),
                ("Source", "SDK_PYTHON_ODOO_1.0"),
                ("OrderID", self.reference),
                ("URL_OK", self._mypos_get_return_url("ok")),
                ("URL_Cancel", self._mypos_get_return_url("cancel")),
                ("URL_Notify", self._mypos_get_return_url("notify")),
                ("Amount", "%.2f" % self.amount),
                ("Currency", self.currency_id.name),
                ("Note", self.reference[:50]),
                ("CustomerEmail", (self.partner_email or "")[:255]),
                ("CustomerFirstNames", (self.partner_name or "").split(" ", 1)[0][:32]),
                ("CustomerLastName", " ".join((self.partner_name or "").split(" ")[1:])[:64]),
                ("CustomerPhone", (self.partner_phone or "")[:32]),
                ("CustomerCountry", self.partner_country_id.code or "BG"),
                ("CustomerCity", (self.partner_city or "")[:50]),
                ("CustomerZIPcode", (self.partner_zip or "")[:20]),
                ("CustomerAddress", (self.partner_address or "")[:100]),
            ]
        )

    def _mypos_get_return_url(self, kind):
        self.ensure_one()
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return f"{base}/payment/mypos/{kind}"

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "mypos" or len(tx) == 1:
            return tx
        reference = notification_data.get("OrderID") or notification_data.get("order_id")
        if not reference:
            raise ValidationError(_("myPOS: missing OrderID in notification"))
        tx = self.search([("reference", "=", reference), ("provider_code", "=", "mypos")])
        if not tx:
            raise ValidationError(
                _("myPOS: no transaction found for reference %s") % reference
            )
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != "mypos":
            return

        signature = notification_data.pop("Signature", None) or notification_data.pop(
            "signature", None
        )
        if not signature:
            self._set_error(_("myPOS: notification missing signature"))
            return

        signed_fields = OrderedDict(
            (k, v) for k, v in notification_data.items() if k != "Signature"
        )
        if not self.provider_id._mypos_verify(signed_fields, signature):
            _logger.warning("myPOS: invalid signature on notification for %s", self.reference)
            self._set_error(_("myPOS: invalid response signature"))
            return

        status = notification_data.get("Status") or notification_data.get("status")
        if status in ("0", 0, "success"):
            self._set_done()
        elif status in ("cancel", "cancelled"):
            self._set_canceled()
        elif status == "pending":
            self._set_pending()
        else:
            self._set_error(_("myPOS: unknown status %s") % status)
