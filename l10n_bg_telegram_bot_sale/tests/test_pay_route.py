# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from .common import TelegramSaleCommon


@tagged("post_install", "-at_install")
class TestTelegramPayRoute(TelegramSaleCommon, HttpCase):
    def setUp(self):
        super().setUp()
        tg_user = self.start_user()
        self.buy()
        self.order = self.env["sale.order"].search(
            [("l10n_bg_telegram_user_id", "=", tg_user.id)]
        )
        # Сайтът от бота трябва да отговаря на домейна на теста
        self.website.domain = self.base_url()

    def _get(self, path):
        return self.url_open(path, allow_redirects=False)

    def test_pay_link_puts_order_in_cart_and_opens_checkout(self):
        response = self._get(
            f"/l10n_bg_telegram/pay/{self.order.id}/{self.order.access_token}"
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("/shop/checkout", response.headers["Location"])
        # Същата сесия: магазинът вижда количката и иска адрес за фактура, а не
        # връща към /shop (празна количка)
        checkout = self._get("/shop/checkout")
        self.assertIn("/shop/address", checkout.headers["Location"])
        self.assertIn(
            f"partner_id={self.order.partner_id.id}", checkout.headers["Location"]
        )

    @mute_logger("odoo.http")
    def test_wrong_token_is_not_found(self):
        response = self._get(f"/l10n_bg_telegram/pay/{self.order.id}/wrong")
        self.assertEqual(response.status_code, 404)

    def test_confirmed_order_goes_to_portal_not_cart(self):
        self.order.action_confirm()
        response = self._get(
            f"/l10n_bg_telegram/pay/{self.order.id}/{self.order.access_token}"
        )
        self.assertIn(f"/my/orders/{self.order.id}", response.headers["Location"])
