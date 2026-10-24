"""Предупреждението „No cost price“ — само за движения, които мърдат стойността.

Пламена, 19.10.2026 (ТГ 173047): вътрешният трансфер СКГПН/ПР/00001 изреждаше
и четирите продукта като „без себестойност“, макар да имат себестойност —
движението между две оценявани локации е без стойност по дизайн.
"""
from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestUnvaluedWarning(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.categ = cls.env["product.category"].create({
            "name": "Unvalued warning goods", "l10n_bg_stock_auto_post": True,
        })
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.stock = cls.warehouse.lot_stock_id
        cls.shelf = cls.env["stock.location"].create({
            "name": "Готова продукция (тест)", "usage": "internal", "location_id": cls.stock.id,
        })
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")

    def _product(self, price):
        return self.env["product.product"].create({
            "name": "Буркан тест %s" % price, "is_storable": True,
            "categ_id": self.categ.id, "standard_price": price,
        })

    def _picking(self, product, source, dest, done=True):
        ptype = self.warehouse.int_type_id if source.usage == "internal" else self.warehouse.in_type_id
        picking = self.env["stock.picking"].create({
            "picking_type_id": ptype.id, "location_id": source.id, "location_dest_id": dest.id,
            "move_ids": [Command.create({
                "product_id": product.id, "product_uom_qty": 4.0,
                "location_id": source.id, "location_dest_id": dest.id,
            })],
        })
        picking.action_confirm()
        if done:
            if source.usage == "internal":
                self.env["stock.quant"]._update_available_quantity(product, source, 4.0)
            picking.action_assign()
            picking.move_ids.quantity = 4.0
            picking.move_ids.picked = True
            picking._action_done()
        return picking

    def test_internal_transfer_between_valued_locations_is_not_flagged(self):
        product = self._product(1.84)
        picking = self._picking(product, self.stock, self.shelf)
        self.assertEqual(picking.move_ids.state, "done")
        self.assertFalse(picking._l10n_bg_unvalued_products())
        self.assertFalse(picking.l10n_bg_unvalued_warning)

    def test_internal_transfer_of_product_without_cost_is_not_flagged_either(self):
        # дори без себестойност вътрешният трансфер не носи стойност — не е грешка
        picking = self._picking(self._product(0.0), self.stock, self.shelf, done=False)
        self.assertFalse(picking._l10n_bg_unvalued_products())

    def test_receipt_without_cost_is_still_flagged(self):
        product = self._product(0.0)
        picking = self._picking(product, self.supplier, self.stock, done=False)
        self.assertEqual(picking._l10n_bg_unvalued_products(), product)
