# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.http import Controller, request, route


class WebsiteSaleInvoiceRequest(Controller):

    @route("/shop/l10n_bg/invoice_request", type="jsonrpc", auth="public", website=True)
    def l10n_bg_invoice_request(self, requested=False):
        order_sudo = request.cart
        if not order_sudo:
            return False
        order_sudo.l10n_bg_invoice_requested = bool(requested)
        return order_sudo.l10n_bg_invoice_requested
