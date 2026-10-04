# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _
from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale

EIK_LENGTHS = (9, 13)
# маркерът казва, че формата носи отметката — без него липсващата отметка
# не значи „не искам фактура“ (например формата за доставка)
FORM_MARKER = "l10n_bg_invoice_request_form"
FORM_FIELD = "l10n_bg_invoice_requested"


class WebsiteSaleInvoiceRequest(WebsiteSale):

    @route("/shop/l10n_bg/invoice_request", type="jsonrpc", auth="public", website=True)
    def l10n_bg_invoice_request(self, requested=False):
        order_sudo = request.cart
        if not order_sudo:
            return False
        order_sudo.l10n_bg_invoice_requested = bool(requested)
        invoice_partner = order_sudo.partner_invoice_id
        has_company = bool(
            invoice_partner.commercial_company_name
            and (invoice_partner.vat or invoice_partner.l10n_bg_uic)
        )
        return {
            "requested": order_sudo.l10n_bg_invoice_requested,
            # фирмата липсва ⇒ формата за адреса за фактура, иначе остава в checkout
            "billing_url": (
                False if has_company
                else "/shop/address?partner_id=%s&address_type=billing" % invoice_partner.id
            ),
        }

    def _prepare_address_form_values(self, *args, order_sudo=False, **kwargs):
        values = super()._prepare_address_form_values(*args, order_sudo=order_sudo, **kwargs)
        # фирмените полета се рендират винаги; видимостта им следва отметката (JS)
        if order_sudo:
            values["display_b2b_fields"] = True
        return values

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)
        uic = (address_values.get("l10n_bg_uic") or "").replace(" ", "")
        if uic:
            address_values["l10n_bg_uic"] = uic
            if uic.isdigit() and len(uic) in EIK_LENGTHS:
                address_values["l10n_bg_uic_type"] = "bg_uic"
        if form_data.get(FORM_MARKER) and request.cart:
            request.cart.l10n_bg_invoice_requested = bool(form_data.get(FORM_FIELD))
        return address_values, extra_form_data

    def _validate_address_values(
        self, address_values, partner_sudo, address_type, use_delivery_as_billing,
        required_fields, **kwargs,
    ):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, use_delivery_as_billing,
            required_fields, **kwargs,
        )
        # поискана фактура ⇒ фирма и ЕИК или ДДС номер, без тях фактура не става
        if kwargs.get(FORM_FIELD) and (address_type == "billing" or use_delivery_as_billing):
            if "company_name" in address_values and not address_values.get("company_name"):
                missing_fields.add("company_name")
            if (
                "vat" in address_values or "l10n_bg_uic" in address_values
            ) and not (address_values.get("vat") or address_values.get("l10n_bg_uic")):
                missing_fields.update({"vat", "l10n_bg_uic"})
                error_messages.append(_("An invoice needs the UIC (EIK) or the VAT number."))
        return invalid_fields, missing_fields, error_messages
