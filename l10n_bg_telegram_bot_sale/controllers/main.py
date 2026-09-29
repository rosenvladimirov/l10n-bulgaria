# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.tools import consteq

from ..models.sale_order import PAY_ROUTE


class L10nBgTelegramPay(http.Controller):
    @http.route(
        f"{PAY_ROUTE}/<int:order_id>/<string:access_token>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def pay(self, order_id, access_token, **_kwargs):
        """Слага поръчката от бота в количката на сесията и отваря плащането.

        Оттук нататък всичко е стандартният път на магазина: адрес за фактура,
        доставчик на плащане, потвърждение на поръчката.
        """
        order = request.env["sale.order"].sudo().browse(order_id).exists()
        if (
            not order
            or not order.access_token
            or not consteq(order.access_token, access_token)
        ):
            raise NotFound()
        if order.state != "draft" or order.website_id != request.website:
            # Платена или от друг сайт — показваме поръчката, не количка
            return request.redirect(order.get_portal_url())
        request.session["sale_order_id"] = order.id
        return request.redirect("/shop/checkout?try_skip_step=true")
