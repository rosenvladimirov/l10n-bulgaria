# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        # Поръчка на едро: доставката е от избрания склад и до избрания
        # адрес (ADR specs/pos-b2b-wholesale/0002). Сборните доставки при
        # затваряне на сесията (няколко поръчки) остават на ядрото.
        order = lines.order_id
        if len(order) == 1 and order.l10n_bg_is_b2b:
            warehouse = order.l10n_bg_warehouse_id
            if warehouse and warehouse != picking_type.warehouse_id:
                picking_type = warehouse.pos_type_id or warehouse.out_type_id
                location_dest_id = (
                    order.partner_id.property_stock_customer.id
                    or picking_type.default_location_dest_id.id
                    or location_dest_id
                )
            if order.l10n_bg_shipping_partner_id:
                partner = order.l10n_bg_shipping_partner_id
        return super()._create_picking_from_pos_order_lines(
            location_dest_id, lines, picking_type, partner
        )
