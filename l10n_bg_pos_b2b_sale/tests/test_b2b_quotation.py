# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_bg_pos_b2b.tests.common import B2bPosCommon


@tagged("post_install", "-at_install")
class TestB2bQuotation(B2bPosCommon):
    """Поръчката на едро се запазва като чернова SO (ADR 0003, фаза 1)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.delivery = cls.env["res.partner"].create({
            "name": "BG Buyer Warehouse",
            "type": "delivery",
            "parent_id": cls.b2b_company.id,
            "street": "5 Industrial Zone",
            "city": "Plovdiv",
            "country_id": cls.bg.id,
        })
        cls.term = cls.env.ref("account.account_payment_term_30days")
        # касиерът, който запазва оферти, има права в Продажби (CONFIGURE)
        cls.env.user.group_ids += cls.env.ref("sales_team.group_sale_salesman")

    def _payload(self, **kwargs):
        payload = {
            "partner_id": self.b2b_company.id,
            "client_order_ref": "PO-2026-15",
            "shipping_date": "2026-10-15",
            "pos_reference": "POS/0001",
            "form": {
                "shipping_partner_id": self.delivery.id,
                "payment_term_id": self.term.id,
                "validity_date": "2026-11-09",
                "note": "Delivery by truck",
            },
            "lines": [{
                "uuid": "line-1",
                "product_id": self.product1.id,
                "qty": 3,
                "price_unit": 12.5,
                "discount": 10,
            }],
        }
        payload.update(kwargs)
        return payload

    def test_save_creates_draft_quotation(self):
        self.open_new_session()
        result = self.config.l10n_bg_b2b_save_quotation(self._payload())
        order = self.env["sale.order"].browse(result["id"])
        self.assertEqual(order.state, "draft")
        self.assertEqual(result["name"], order.name)
        self.assertEqual(order.partner_id, self.b2b_company)
        self.assertEqual(order.partner_shipping_id, self.delivery)
        self.assertEqual(order.payment_term_id, self.term)
        self.assertEqual(str(order.validity_date), "2026-11-09")
        self.assertEqual(order.commitment_date.date().isoformat(), "2026-10-15")
        self.assertEqual(order.client_order_ref, "PO-2026-15")
        self.assertEqual(order.origin, "POS/0001")
        self.assertIn("Delivery by truck", str(order.note))
        self.assertEqual(order.warehouse_id, self.config.warehouse_id)
        line = order.order_line
        self.assertEqual(len(line), 1)
        self.assertEqual((line.product_uom_qty, line.price_unit, line.discount), (3, 12.5, 10))
        self.assertIn("sale.report_saleorder_pro_forma", result["reports"]["pro_forma"])

    def test_save_again_updates_the_same_quotation(self):
        self.open_new_session()
        first = self.config.l10n_bg_b2b_save_quotation(self._payload())
        line_id = first["lines"]["line-1"]["id"]
        product2 = self.create_product("Product 2", self.categ_basic, 4.0, 1)
        second = self.config.l10n_bg_b2b_save_quotation(self._payload(
            sale_order_id=first["id"],
            lines=[
                {"uuid": "line-1", "product_id": self.product1.id, "qty": 7, "price_unit": 10, "discount": 0},
                {"uuid": "line-2", "product_id": product2.id, "qty": 1, "price_unit": 4, "discount": 0},
            ],
        ))
        self.assertEqual(first["id"], second["id"])
        order = self.env["sale.order"].browse(second["id"])
        # редът е обновен НА МЯСТО (същият id) — закаченото за него остава
        self.assertEqual(second["lines"]["line-1"]["id"], line_id)
        self.assertEqual(order.order_line.filtered(lambda l: l.id == line_id).product_uom_qty, 7)
        self.assertEqual(len(order.order_line), 2)
        # ред, изтрит в касата, се трие и в офертата
        third = self.config.l10n_bg_b2b_save_quotation(self._payload(
            sale_order_id=first["id"],
            lines=[{"uuid": "line-2", "product_id": product2.id, "qty": 2, "price_unit": 4, "discount": 0}],
        ))
        self.assertEqual(list(third["lines"]), ["line-2"])
        self.assertEqual(len(order.order_line), 1)
        # ред, добавен в Продажби (без връзка към касата), не се трие
        manual = self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product1.id, "product_uom_qty": 1,
        })
        self.config.l10n_bg_b2b_save_quotation(self._payload(
            sale_order_id=first["id"],
            lines=[{"uuid": "line-2", "product_id": product2.id, "qty": 3, "price_unit": 4, "discount": 0}],
        ))
        self.assertIn(manual, order.order_line)

    def test_confirmed_quotation_is_not_changed(self):
        self.open_new_session()
        result = self.config.l10n_bg_b2b_save_quotation(self._payload())
        self.env["sale.order"].browse(result["id"]).action_confirm()
        with self.assertRaises(UserError):
            self.config.l10n_bg_b2b_save_quotation(self._payload(sale_order_id=result["id"]))

    def test_foreign_address_is_dropped(self):
        self.open_new_session()
        result = self.config.l10n_bg_b2b_save_quotation(self._payload(
            form={"shipping_partner_id": self.person.id},
        ))
        order = self.env["sale.order"].browse(result["id"])
        self.assertEqual(
            order.partner_shipping_id.id,
            self.b2b_company.address_get(["delivery"])["delivery"],
        )

    def test_needs_customer_and_lines(self):
        self.open_new_session()
        with self.assertRaises(UserError):
            self.config.l10n_bg_b2b_save_quotation(self._payload(partner_id=False))
        with self.assertRaises(UserError):
            self.config.l10n_bg_b2b_save_quotation(self._payload(lines=[]))

    def test_pos_order_keeps_the_quotation_link(self):
        self.open_new_session()
        result = self.config.l10n_bg_b2b_save_quotation(self._payload())
        order = self._sync(self.create_ui_order_data(
            [(self.product1, 1)], customer=self.b2b_company, is_invoiced=True,
            pos_order_ui_args={
                "l10n_bg_wholesale": True,
                "l10n_bg_b2b_form": {"sale_order_id": result["id"]},
            },
        ))
        self.assertEqual(order.l10n_bg_sale_order_id.id, result["id"])
