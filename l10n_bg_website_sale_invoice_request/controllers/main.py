# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _
from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale

COMPANY_FIELDS = ("name", "l10n_bg_uic", "vat", "street", "city", "zip", "country_id")


class WebsiteSaleInvoiceRequest(WebsiteSale):

    @route("/shop/l10n_bg/invoice_request", type="jsonrpc", auth="public", website=True)
    def l10n_bg_invoice_request(self, requested=False):
        order_sudo = request.cart
        if not order_sudo:
            return False
        if not requested:
            order_sudo._l10n_bg_unset_invoice_company()
            return {"requested": False}
        order_sudo.l10n_bg_invoice_requested = True
        company = order_sudo._l10n_bg_invoice_company()
        if company:
            order_sudo._l10n_bg_bind_invoice_company(company)
            return {"requested": True}
        # фирмата още липсва ⇒ отделната форма „Фирма за фактура“
        return {"requested": True, "form_url": "/shop/l10n_bg/invoice_company"}

    @route(
        "/shop/l10n_bg/invoice_company", type="http", auth="public", website=True,
        methods=["GET", "POST"], sitemap=False,
    )
    def l10n_bg_invoice_company(self, **post):
        order_sudo = request.cart
        if not order_sudo:
            return request.redirect("/shop/cart")
        if order_sudo._is_anonymous_cart():
            return request.redirect("/shop/address")
        company = order_sudo._l10n_bg_invoice_company()
        person = order_sudo._l10n_bg_delivery_person()
        values = {
            "name": company.name or "",
            "l10n_bg_uic": company.l10n_bg_uic or "",
            "vat": company.vat or "",
            "street": company.street or person.street or "",
            "city": company.city or person.city or "",
            "zip": company.zip or person.zip or "",
            "country_id": (company.country_id or person.country_id or request.env.ref("base.bg")).id,
        }
        errors = {}
        if request.httprequest.method == "POST":
            for field in COMPANY_FIELDS:
                values[field] = (post.get(field) or "").strip()
            values["l10n_bg_uic"] = values["l10n_bg_uic"].replace(" ", "")
            values["vat"] = values["vat"].replace(" ", "").upper()
            values["country_id"] = int(values["country_id"] or 0) or request.env.ref("base.bg").id
            for field in ("name", "street", "city"):
                if not values[field]:
                    errors[field] = _("Required")
            if not (values["l10n_bg_uic"] or values["vat"]):
                errors["l10n_bg_uic"] = _("An invoice needs the UIC (EIK) or the VAT number.")
            if not errors:
                order_sudo._l10n_bg_set_invoice_company(values)
                return request.redirect("/shop/checkout")
        return request.render("l10n_bg_website_sale_invoice_request.invoice_company_form", {
            "website_sale_order": order_sudo,
            "values": values,
            "errors": errors,
            "countries": request.env["res.country"].sudo().search([]),
        })

    def _prepare_address_form_values(self, *args, order_sudo=False, **kwargs):
        values = super()._prepare_address_form_values(*args, order_sudo=order_sudo, **kwargs)
        # адресът на сайта е само за доставка — фирмата е в „Фирма за фактура“
        if order_sudo:
            values["display_b2b_fields"] = False
        return values
