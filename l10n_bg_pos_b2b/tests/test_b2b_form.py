# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.tests import tagged

from .common import B2bPosCommon


@tagged("post_install", "-at_install")
class TestB2bForm(B2bPosCommon):
    """Формата за едро като в продажбата (ADR specs/pos-b2b-wholesale/0002)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.invoice_address = Partner.create({
            "name": "BG Buyer Accounting",
            "type": "invoice",
            "parent_id": cls.b2b_company.id,
            "street": "3 Shipka Str",
            "city": "Sofia",
            "country_id": cls.bg.id,
        })
        cls.delivery_address = Partner.create({
            "name": "BG Buyer Warehouse",
            "type": "delivery",
            "parent_id": cls.b2b_company.id,
            "street": "5 Industrial Zone",
            "city": "Plovdiv",
            "country_id": cls.bg.id,
        })
        cls.term = cls.env.ref("account.account_payment_term_30days")
        cls.salesperson = cls.env.ref("base.user_admin")

    def _form_order(self, form, **kwargs):
        args = {"l10n_bg_wholesale": True, "l10n_bg_b2b_form": form}
        args.update(kwargs)
        return self._sync(self.create_ui_order_data(
            [(self.product1, 2)], customer=self.b2b_company, is_invoiced=True,
            pos_order_ui_args=args,
        ))

    def test_form_goes_to_the_invoice(self):
        self.open_new_session()
        order = self._form_order({
            "invoice_partner_id": self.invoice_address.id,
            "shipping_partner_id": self.delivery_address.id,
            "payment_term_id": self.term.id,
            "salesperson_id": self.salesperson.id,
            "validity_date": "2026-11-30",
            "note": "Delivery by truck",
        })
        move = order.account_move
        self.assertEqual(move.partner_id, self.invoice_address)
        self.assertEqual(move.partner_shipping_id, self.delivery_address)
        self.assertEqual(move.invoice_payment_term_id, self.term)
        self.assertEqual(move.invoice_user_id, self.salesperson)
        self.assertIn("Delivery by truck", str(move.narration))
        self.assertEqual(str(order.l10n_bg_validity_date), "2026-11-30")

    def test_form_drops_foreign_values(self):
        # адрес на друг клиент и склад на друга фирма не се приемат,
        # без грешка при синхронизацията
        other_company = self.env["res.company"].create({"name": "Other BG Co"})
        other_warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", other_company.id)], limit=1,
        )
        self.open_new_session()
        order = self._form_order({
            "invoice_partner_id": self.person.id,
            "warehouse_id": other_warehouse.id or 999999,
            "payment_term_id": "x",
        })
        self.assertFalse(order.l10n_bg_invoice_partner_id)
        self.assertFalse(order.l10n_bg_warehouse_id)
        self.assertFalse(order.l10n_bg_payment_term_id)
        self.assertEqual(
            order.account_move.partner_id.id,
            self.b2b_company.address_get(["invoice"])["invoice"],
        )

    def test_form_warehouse_and_delivery_address_on_picking(self):
        warehouse = self.env["stock.warehouse"].create({
            "name": "Plovdiv WH",
            "code": "PLV",
            "company_id": self.env.company.id,
        })
        self.assertNotEqual(warehouse, self.config.warehouse_id)
        self.open_new_session()
        order = self._form_order({
            "shipping_partner_id": self.delivery_address.id,
            "warehouse_id": warehouse.id,
        })
        self.assertEqual(order.l10n_bg_warehouse_id, warehouse)
        self.assertTrue(order.picking_ids, "the picking is made at once")
        self.assertEqual(order.picking_ids.picking_type_id.warehouse_id, warehouse)
        self.assertEqual(order.picking_ids.partner_id, self.delivery_address)

    def test_form_options(self):
        options = self.config.l10n_bg_b2b_form_options(self.b2b_company.id)
        invoice_ids = [a["id"] for a in options["invoice_addresses"]]
        delivery_ids = [a["id"] for a in options["delivery_addresses"]]
        self.assertIn(self.invoice_address.id, invoice_ids)
        self.assertNotIn(self.delivery_address.id, invoice_ids)
        self.assertIn(self.delivery_address.id, delivery_ids)
        self.assertEqual(options["defaults"]["invoice_partner_id"], self.invoice_address.id)
        self.assertEqual(options["defaults"]["shipping_partner_id"], self.delivery_address.id)
        self.assertEqual(options["defaults"]["warehouse_id"], self.config.warehouse_id.id)
        self.assertIn(self.term.id, [t["id"] for t in options["payment_terms"]])
        # без клиент — празни адреси, без грешка
        empty = self.config.l10n_bg_b2b_form_options(False)
        self.assertEqual(empty["invoice_addresses"], [])
        self.assertFalse(empty["defaults"]["invoice_partner_id"])
