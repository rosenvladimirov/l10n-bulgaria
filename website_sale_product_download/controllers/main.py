# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request


class WebsiteSaleProductDownload(http.Controller):
    @http.route(
        "/shop/download",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
        sitemap=False,
        readonly=False,
    )
    def shop_product_download(self, product_id=None, **kwargs):
        """Сваля файла на избрания вариант на безплатен продукт.

        auth="user": непознат посетител минава през вход и се връща тук
        със същия вариант (параметрите остават в redirect).
        """
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return request.not_found()
        product = request.env["product.product"].sudo().browse(product_id).exists()
        if not product:
            return request.not_found()
        template = product.product_tmpl_id
        # Същите проверки като за количката: публикуван, активен, от този сайт
        if not template.website_download or not product._is_add_to_cart_allowed():
            return request.not_found()
        # Цената по ценовата листа на сайта, не само тази в продукта
        if product._get_contextual_price():
            return request.redirect(template.website_url)
        document = template._get_website_download_document(product)
        if not document:
            return request.redirect(template.website_url)
        request.env["website.product.download"].sudo().create(
            {
                "product_id": product.id,
                "document_id": document.id,
                "file_name": document.name,
                "user_id": request.env.user.id,
                "partner_id": request.env.user.partner_id.id,
                "website_id": request.website.id,
            }
        )
        return (
            request.env["ir.binary"]
            ._get_stream_from(document.ir_attachment_id)
            .get_response(as_attachment=True)
        )
