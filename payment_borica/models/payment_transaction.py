# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from collections import OrderedDict
from datetime import datetime, timezone

from odoo import _, api, fields, models
from odoo.tools import urls

from odoo.addons.payment.logging import get_payment_logger

from ..const import SALE_SIGN_FIELDS
from ..controllers.main import BoricaController

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    borica_order = fields.Char(
        string="Borica ORDER",
        help="6-digit order number sent to Borica and echoed back in its response.",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )

    def _get_specific_rendering_values(self, processing_values):
        if self.provider_code != "borica":
            return super()._get_specific_rendering_values(processing_values)

        provider = self.provider_id
        self.borica_order = self._borica_order_id()
        order_id = self.borica_order
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        nonce = provider._borica_nonce()

        signing_values = OrderedDict(
            [
                ("TERMINAL", provider.borica_terminal or ""),
                ("TRTYPE", "1"),
                ("AMOUNT", f"{self.amount:.2f}"),
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
                (
                    "LANG",
                    (self.partner_lang or provider.borica_lang or "EN")[:2].upper(),
                ),
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
        """ORDER по спецификацията е до 6 цифри.

        Вадим го от id на транзакцията, не от цифрите в референцията: „S00012-1“ и
        „S0001-21“ дават едни и същи цифри, а id е уникален за първия милион.
        """
        self.ensure_one()
        return str(self.id % 1000000).rjust(6, "0")

    def _borica_get_return_url(self):
        self.ensure_one()
        return urls.urljoin(
            self.provider_id.get_base_url(), BoricaController._return_url
        )

    @api.model
    def _search_by_reference(self, provider_code, payment_data):
        # Борика връща само ORDER (6 цифри), не нашата референция
        if provider_code != "borica":
            return super()._search_by_reference(provider_code, payment_data)
        order = (payment_data.get("ORDER") or "").strip()
        if not order:
            _logger.warning("Received Borica payment data with missing ORDER")
            return self
        tx = self.search(
            [
                ("provider_code", "=", "borica"),
                ("borica_order", "=", order.rjust(6, "0")),
            ],
            order="id desc",
            limit=1,
        )
        if not tx:
            _logger.warning("No Borica transaction found matching ORDER %s.", order)
        return tx

    def _extract_amount_data(self, payment_data):
        if self.provider_code != "borica":
            return super()._extract_amount_data(payment_data)
        amount = payment_data.get("AMOUNT")
        return {
            "amount": float(amount) if amount else 0.0,
            "currency_code": payment_data.get("CURRENCY"),
        }

    def _apply_updates(self, payment_data):
        if self.provider_code != "borica":
            return super()._apply_updates(payment_data)

        # Подписът е проверен в контролера, преди `_process`
        self.provider_reference = payment_data.get("INT_REF") or payment_data.get("RRN")

        action = payment_data.get("ACTION")
        rc = payment_data.get("RC")
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
            self._set_error(
                _("Borica: unknown ACTION=%(action)s RC=%(rc)s", action=action, rc=rc)
            )
