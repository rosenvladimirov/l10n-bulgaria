# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
from urllib.parse import parse_qs, urlparse

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestProductDownload(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env["website"].get_current_website()
        attribute = cls.env["product.attribute"].create(
            {
                "name": "Operating System",
                "create_variant": "always",
                "value_ids": [(0, 0, {"name": "Windows"}), (0, 0, {"name": "Linux"})],
            }
        )
        cls.template = cls.env["product.template"].create(
            {
                "name": "Label Designer",
                "type": "service",
                "list_price": 0.0,
                "is_published": True,
                "website_download": True,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [(6, 0, attribute.value_ids.ids)],
                        },
                    )
                ],
            }
        )
        cls.windows, cls.linux = cls.template.product_variant_ids.sorted(
            lambda p: p.product_template_attribute_value_ids.name != "Windows"
        )
        Document = cls.env["product.document"]
        cls.doc_windows = Document.create(
            {
                "name": "setup-win64.exe",
                "datas": base64.b64encode(b"WINDOWS INSTALLER"),
                "res_model": "product.product",
                "res_id": cls.windows.id,
                "attached_on_sale": "sale_order",
            }
        )
        cls.doc_linux = Document.create(
            {
                "name": "app-x86_64.AppImage",
                "datas": base64.b64encode(b"LINUX APPIMAGE"),
                "res_model": "product.product",
                "res_id": cls.linux.id,
                "attached_on_sale": "sale_order",
            }
        )
        cls.customer = new_test_user(
            cls.env,
            login="downloader",
            password="downloader",
            groups="base.group_portal",
        )

    def _download(self, product):
        return self.url_open(
            f"/shop/download/file?product_id={product.id}", allow_redirects=False
        )

    def test_public_visitor_signs_in_first(self):
        response = self.url_open(
            f"/shop/download?product_id={self.linux.id}", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        location = urlparse(response.headers["Location"])
        self.assertEqual(location.path, "/web/login")
        # След входа се връща към същия вариант
        self.assertIn(
            f"product_id={self.linux.id}", parse_qs(location.query)["redirect"][0]
        )
        self.assertFalse(self.env["website.product.download"].search([]))

    def test_each_variant_gets_its_own_file_and_is_logged(self):
        self.authenticate("downloader", "downloader")
        for product, document, content in (
            (self.windows, self.doc_windows, b"WINDOWS INSTALLER"),
            (self.linux, self.doc_linux, b"LINUX APPIMAGE"),
        ):
            response = self._download(product)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, content)
            self.assertIn(document.name, response.headers["Content-Disposition"])
        logs = self.env["website.product.download"].search([], order="id")
        self.assertEqual(
            logs.mapped("file_name"), ["setup-win64.exe", "app-x86_64.AppImage"]
        )
        self.assertEqual(logs.partner_id, self.customer.partner_id)
        self.assertEqual(self.template.website_download_count, 2)

    def test_template_document_is_the_fallback(self):
        self.doc_linux.unlink()
        common = self.env["product.document"].create(
            {
                "name": "readme.txt",
                "datas": base64.b64encode(b"COMMON"),
                "res_model": "product.template",
                "res_id": self.template.id,
                "attached_on_sale": "sale_order",
            }
        )
        self.authenticate("downloader", "downloader")
        self.assertEqual(self._download(self.linux).content, b"COMMON")
        # Документът на варианта е пред общия
        self.assertEqual(self._download(self.windows).content, b"WINDOWS INSTALLER")
        self.assertTrue(common)

    def test_hidden_or_quotation_documents_are_not_given(self):
        self.doc_linux.attached_on_sale = "hidden"
        self.authenticate("downloader", "downloader")
        response = self._download(self.linux)
        self.assertEqual(response.status_code, 303)
        self.assertFalse(self.env["website.product.download"].search([]))

    def test_refused_without_the_flag_or_when_unpublished(self):
        self.authenticate("downloader", "downloader")
        self.template.website_download = False
        self.assertEqual(self._download(self.windows).status_code, 404)
        self.template.website_download = True
        self.template.is_published = False
        self.assertEqual(self._download(self.windows).status_code, 404)
        self.assertEqual(self._download(self.env["product.product"]).status_code, 404)
        self.assertEqual(
            self.url_open("/shop/download?product_id=abc").status_code, 404
        )

    def test_a_variant_with_a_price_is_not_free(self):
        # Цената на варианта (price_extra) прави продукта платен
        self.windows.product_template_attribute_value_ids.price_extra = 10.0
        self.authenticate("downloader", "downloader")
        response = self._download(self.windows)
        self.assertEqual(response.status_code, 303)
        self.assertNotIn("/web/login", response.headers["Location"])
        self.assertFalse(self.env["website.product.download"].search([]))

    def test_paid_product_cannot_be_marked(self):
        with self.assertRaises(ValidationError):
            self.template.list_price = 299.0

    def test_product_page_shows_download_instead_of_cart(self):
        page = self.url_open(self.template.website_url).text
        self.assertIn('id="o_wsale_download"', page)
        self.assertIn('formaction="/shop/download"', page)
        self.assertNotIn('id="add_to_cart"', page)
        self.template.website_download = False
        page = self.url_open(self.template.website_url).text
        self.assertNotIn('id="o_wsale_download"', page)
        self.assertIn('id="add_to_cart"', page)

    def test_after_sign_in_a_page_starts_the_download(self):
        # Страница, а не файл: иначе формата за вход остава да се върти
        self.authenticate("downloader", "downloader")
        response = self.url_open(f"/shop/download?product_id={self.linux.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["Content-Type"])
        file_url = f"/shop/download/file?product_id={self.linux.id}"
        self.assertIn(f'content="1;url={file_url}"', response.text)
        self.assertIn(f'href="{file_url}"', response.text)
        self.assertIn("app-x86_64.AppImage", response.text)
        # Страницата само показва; записва се свалянето на файла
        self.assertFalse(self.env["website.product.download"].search([]))
        self.assertEqual(self.url_open(file_url).content, b"LINUX APPIMAGE")
        self.assertEqual(len(self.env["website.product.download"].search([])), 1)

    def test_public_visitor_cannot_get_the_file_directly(self):
        response = self._download(self.windows)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/web/login", response.headers["Location"])
