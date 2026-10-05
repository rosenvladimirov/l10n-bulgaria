# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from datetime import date, datetime

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged("post_install", "-at_install")
class TestInvoiceRequest(TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.country_id = cls.env.ref("base.bg")
        cls.random_customer = cls.env.ref("l10n_bg_config.partner_random_customer")
        cls.website = cls.env["website"].create({"name": "Shop", "company_id": cls.company.id})
        # „по доставка“: месечната фактура трябва да вземе и неекспедираното
        cls.product = cls.company_data["product_service_delivery"]

    def _order(self, website=True, requested=False, when=datetime(2026, 10, 15, 10, 0)):
        return self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "website_id": self.website.id if website else False,
            "l10n_bg_invoice_requested": requested,
            "date_order": when,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 2})],
        })

    def test_confirm_without_request_uses_random_customer(self):
        order = self._order()
        order.action_confirm()
        self.assertEqual(order.partner_invoice_id, self.random_customer)
        self.assertEqual(order.partner_id, self.partner_a)

    def test_confirm_with_request_keeps_billing_address(self):
        order = self._order(requested=True)
        order.action_confirm()
        self.assertEqual(order.partner_invoice_id, self.partner_a)

    def test_backend_order_untouched(self):
        order = self._order(website=False)
        order.action_confirm()
        self.assertEqual(order.partner_invoice_id, self.partner_a)

    def test_monthly_sales_report(self):
        orders = self._order() | self._order()
        orders.action_confirm()
        orders.date_order = datetime(2026, 10, 15, 10, 0)
        requested = self._order(requested=True)
        requested.action_confirm()
        current = self._order()
        current.action_confirm()
        current.date_order = datetime(2026, 11, 1, 0, 30)
        with freeze_time("2026-11-01 02:00:00"):
            self.env["sale.order"]._cron_l10n_bg_invoice_random_customer()
        moves = orders.invoice_ids
        self.assertEqual(len(moves), 1, "one invoice for all random customer orders")
        self.assertEqual(moves.partner_id, self.random_customer)
        self.assertEqual(moves.l10n_bg_document_type, "81")
        self.assertEqual(moves.invoice_date, date(2026, 10, 31))
        self.assertEqual(moves.state, "posted")
        self.assertEqual(moves.amount_untaxed, 4 * self.product.list_price)
        self.assertFalse(requested.invoice_ids, "orders with an invoice request stay out")
        self.assertFalse(current.invoice_ids, "orders of the current month wait for the next run")

    def _person_order(self):
        person = self.env["res.partner"].create({
            "name": "Иван Купувач", "email": "ivan@example.com", "street": "Плиска 23",
            "city": "Разград", "country_id": self.env.ref("base.bg").id,
        })
        return person, self.env["sale.order"].create({
            "partner_id": person.id, "website_id": self.website.id,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})],
        })

    def test_invoice_company_becomes_customer(self):
        # „Искам фактура“: клиентът е фирмата, лицето — неин адрес за доставка
        person, order = self._person_order()
        company = order._l10n_bg_set_invoice_company({
            "name": "Тест Фирма ЕООД", "l10n_bg_uic": "202588745", "vat": "",
            "street": "Бул. България 1", "city": "София", "zip": "1000",
            "country_id": self.env.ref("base.bg").id,
        })
        self.assertTrue(company.is_company)
        self.assertEqual(company.l10n_bg_uic, "202588745")
        self.assertEqual(company.email, "ivan@example.com")
        self.assertEqual(person.parent_id, company)
        self.assertEqual(person.type, "delivery")
        self.assertEqual(order.partner_id, company)
        self.assertEqual(order.partner_invoice_id, company)
        self.assertEqual(order.partner_shipping_id, person)
        self.assertTrue(order.l10n_bg_invoice_requested)
        order.action_confirm()
        self.assertEqual(order.partner_invoice_id, company, "no random customer for a requested invoice")

    def test_existing_company_reused_not_overwritten(self):
        # фирма от Търговския регистър: същата, данните ѝ не се презаписват
        existing = self.env["res.partner"].create({
            "name": "Заварена ООД", "is_company": True, "l10n_bg_uic": "131468980",
            "street": "Адрес от ТР", "city": "Пловдив",
        })
        person, order = self._person_order()
        company = order._l10n_bg_set_invoice_company({
            "name": "Друго име", "l10n_bg_uic": "131468980", "vat": "",
            "street": "Друг адрес", "city": "Варна", "zip": "9000",
            "country_id": self.env.ref("base.bg").id,
        })
        self.assertEqual(company, existing)
        self.assertEqual(existing.name, "Заварена ООД")
        self.assertEqual(existing.street, "Адрес от ТР")
        self.assertEqual(existing.zip, "9000", "empty fields are filled")
        self.assertEqual(person.parent_id, existing)

    def test_unset_returns_to_person(self):
        person, order = self._person_order()
        order._l10n_bg_set_invoice_company({
            "name": "Тест Фирма ЕООД", "l10n_bg_uic": "202588745", "vat": "",
            "street": "Бул. България 1", "city": "София", "zip": "",
            "country_id": self.env.ref("base.bg").id,
        })
        order._l10n_bg_unset_invoice_company()
        self.assertEqual(order.partner_id, person)
        self.assertFalse(order.l10n_bg_invoice_requested)
        order.action_confirm()
        self.assertEqual(order.partner_invoice_id, self.random_customer)

    def test_other_contacts_hidden(self):
        # втори купувач със същия ЕИК не вижда и не пипа адреса на първия
        company_values = {
            "name": "Обща Фирма ЕООД", "l10n_bg_uic": "205000001", "vat": "",
            "street": "Бул. България 1", "city": "София", "zip": "1000",
            "country_id": self.env.ref("base.bg").id,
        }
        first, order1 = self._person_order()
        order1._l10n_bg_set_invoice_company(company_values)
        second, order2 = self._person_order()
        order2._l10n_bg_set_invoice_company(company_values)
        self.assertEqual(order1.partner_id, order2.partner_id)
        visible = order2._l10n_bg_visible_partners()
        self.assertIn(second, visible)
        self.assertNotIn(first, visible)
        self.assertFalse(first._can_be_edited_by_current_customer(order_sudo=order2))
