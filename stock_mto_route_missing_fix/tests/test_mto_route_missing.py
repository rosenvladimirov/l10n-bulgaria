from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMtoRouteMissing(TransactionCase):
    """Складът трябва да се записва и когато глобалният MTO маршрут липсва."""

    def _drop_mto_route(self):
        # Ядрото първо търси по външен идентификатор, после по име (с
        # active_test=False) — за да е реалистичен тестът, трябва да няма нито
        # едното, нито другото.
        route = self.env.ref("stock.route_warehouse0_mto", raise_if_not_found=False)
        if route:
            route.rule_ids.unlink()
            route.unlink()
        leftovers = self.env["stock.route"].with_context(active_test=False).search(
            [("name", "like", "Replenish on Order")]
        )
        leftovers.rule_ids.unlink()
        leftovers.unlink()

    def test_resupply_from_ship_only_warehouse(self):
        """Call site 1: create_resupply_routes()."""
        self._drop_mto_route()
        Warehouse = self.env["stock.warehouse"]
        supplier_wh = Warehouse.create({"name": "MTO Guard Supplier", "code": "MGS"})
        supplied_wh = Warehouse.create({"name": "MTO Guard Supplied", "code": "MGD"})
        self.assertEqual(supplier_wh.delivery_steps, "ship_only")

        supplied_wh.write({"resupply_wh_ids": [(6, 0, supplier_wh.ids)]})

        self.assertTrue(
            supplied_wh.resupply_route_ids,
            "the inter-warehouse resupply route must still be created",
        )
        self.assertFalse(
            self.env["stock.rule"].search(
                [("warehouse_id", "=", supplier_wh.id), ("name", "like", "MTO")]
            ),
            "no MTO rule may be created while the global MTO route is missing",
        )

    def test_delivery_steps_change_on_supplier_warehouse(self):
        """Call site 2: _check_delivery_resupply()."""
        self._drop_mto_route()
        Warehouse = self.env["stock.warehouse"]
        supplier_wh = Warehouse.create({"name": "MTO Guard Src", "code": "MGX"})
        supplied_wh = Warehouse.create({"name": "MTO Guard Dst", "code": "MGY"})
        supplied_wh.write({"resupply_wh_ids": [(6, 0, supplier_wh.ids)]})

        # ship_only -> pick_ship и обратно минават през _check_delivery_resupply
        supplier_wh.write({"delivery_steps": "pick_ship"})
        supplier_wh.write({"delivery_steps": "ship_only"})

        self.assertEqual(supplier_wh.delivery_steps, "ship_only")
