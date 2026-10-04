# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale

EIK_LENGTHS = (9, 13)


class WebsiteSaleInvoiceRequest(WebsiteSale):

    @route("/shop/l10n_bg/invoice_request", type="jsonrpc", auth="public", website=True)
    def l10n_bg_invoice_request(self, requested=False):
        order_sudo = request.cart
        if not order_sudo:
            return False
        order_sudo.l10n_bg_invoice_requested = bool(requested)
        return {
            "requested": order_sudo.l10n_bg_invoice_requested,
            # формата за адреса за фактура — с фирмата, ДДС номера и ЕИК
            "billing_url": "/shop/address?partner_id=%s&address_type=billing"
            % order_sudo.partner_invoice_id.id,
        }

    def _prepare_address_form_values(self, *args, order_sudo=False, **kwargs):
        values = super()._prepare_address_form_values(*args, order_sudo=order_sudo, **kwargs)
        # поискана фактура ⇒ фирмените полета се виждат, дори да са изключени за сайта
        if order_sudo and order_sudo.l10n_bg_invoice_requested:
            values["display_b2b_fields"] = True
        return values

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)
        uic = (address_values.get("l10n_bg_uic") or "").replace(" ", "")
        if uic:
            address_values["l10n_bg_uic"] = uic
            if uic.isdigit() and len(uic) in EIK_LENGTHS:
                address_values["l10n_bg_uic_type"] = "bg_uic"
        return address_values, extra_form_data
