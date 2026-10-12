# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request


class WebsiteSaleProductDownload(http.Controller):
    def _get_download(self, product_id):
        """Вариантът и документът му, или отговорът, когато не се дава.

        Връща (product, document, None) или (None, None, response).
        """
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return None, None, request.not_found()
        product = request.env["product.product"].sudo().browse(product_id).exists()
        if not product:
            return None, None, request.not_found()
        template = product.product_tmpl_id
        # Същите проверки като за количката: публикуван, активен, от този сайт
        if not template.website_download or not product._is_add_to_cart_allowed():
            return None, None, request.not_found()
        # Цената по ценовата листа на сайта, не само тази в продукта
        if product._get_contextual_price():
            return None, None, request.redirect(template.website_url)
        document = template._get_website_download_document(product)
        if not document:
            return None, None, request.redirect(template.website_url)
        return product, document, None

    @staticmethod
    def _human_size(size):
        for unit in ("B", "KB", "MB"):
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    @http.route(
        "/shop/download",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
        sitemap=False,
    )
    def shop_product_download(self, product_id=None, **kwargs):
        """Страница „Свалянето започна“; самият файл идва от /shop/download/file.

        auth="user": непознат посетител минава през вход или регистрация и се
        връща тук със същия вариант. Отговорът е страница, а не файл: иначе
        браузърът остава на формата за вход, а бутонът ѝ се върти безкрай.
        """
        product, document, response = self._get_download(product_id)
        if response:
            return response
        return request.render(
            "website_sale_product_download.download_started",
            {
                "product": product,
                "document": document,
                "file_url": f"/shop/download/file?product_id={product.id}",
                "file_size": self._human_size(document.file_size),
            },
        )

    @http.route(
        "/shop/download/file",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
        sitemap=False,
        readonly=False,
    )
    def shop_product_download_file(self, product_id=None, **kwargs):
        product, document, response = self._get_download(product_id)
        if response:
            return response
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
