# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
from collections import OrderedDict

from odoo import _, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Mirror of IPC/Defines.php::STATUS_* constants from the official PHP SDK.
# Used for human-readable error reporting + idempotency on duplicate notify.
_MYPOS_STATUS = {
    "0": "success",
    "1": "missing_required_params",
    "2": "signature_failed",
    "3": "ipc_error",
    "4": "invalid_sid",
    "5": "invalid_params",
    "6": "invalid_referer",
    "7": "payment_tries_exceeded",
    "8": "transaction_auth_failed",
    "9": "wrong_amount",
    "10": "unsupported_call",
    "11": "inactive_mandate_reference",
    "12": "invalid_mandate_reference",
    "13": "not_sufficient_funds",
    "14": "transaction_not_permitted",
    "15": "exceeded_limit",
    "16": "mandate_already_registered",
    "17": "inactive_account_identifier",
    "18": "invalid_account_identifier",
    "19": "exceeded_account_limits",
    "20": "duplicate_transmission",  # retry — handled idempotently
    "21": "transaction_declined",
    "99": "undefined_error",
}


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
        """Build URL_OK / URL_Cancel / URL_Notify for the gateway.

        myPOS rejects non-HTTPS notify URLs on production ("transaction
        reversal" per the official integration checklist). We enforce it
        early — only test-mode providers are allowed to use http://, and
        even then with a warning so the dev sees the eventual prod gate.
        """
        self.ensure_one()
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        if not base.startswith("https://"):
            if self.provider_id.state != "test":
                raise ValidationError(_(
                    "myPOS: web.base.url must be HTTPS for production transactions "
                    "(current: %s). The gateway reverses transactions whose URL_Notify "
                    "is not SSL-enabled."
                ) % base)
            _logger.warning(
                "myPOS: web.base.url is not HTTPS (%s) — allowed in test mode only. "
                "Set base URL to https:// before switching the provider to production.",
                base,
            )
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

        # Capture gateway transaction reference for downstream Refund/Void calls
        # — IPCRefund / IPCVoid both require IPC_Trnref from the original purchase.
        trnref = notification_data.get("IPC_Trnref") or notification_data.get("Trnref")
        if trnref and not self.provider_reference:
            self.provider_reference = trnref

        status = notification_data.get("Status") or notification_data.get("status")
        status_key = str(status) if status is not None else ""

        if status_key in ("0", "success"):
            self._set_done()
        elif status_key == "20":
            # DUPLICATE_TRANSMISSION — myPOS retried because it didn't get an OK
            # back. Safe no-op: caller returns "OK" so the gateway stops retrying.
            _logger.info(
                "myPOS: duplicate-transmission notify for %s (state=%s) — idempotent no-op",
                self.reference, self.state,
            )
        elif status_key in ("cancel", "cancelled"):
            self._set_canceled()
        elif status_key == "pending":
            self._set_pending()
        else:
            label = _MYPOS_STATUS.get(status_key, "unknown")
            self._set_error(
                _("myPOS: payment failed — status %(code)s (%(label)s)")
                % {"code": status_key or "?", "label": label}
            )
