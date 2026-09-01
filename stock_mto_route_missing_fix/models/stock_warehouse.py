import logging

from odoo import models

_logger = logging.getLogger(__name__)

# Ключът е активен САМО докато тече един от двата защитени вика на ядрото.
# Извън тях поведението остава непроменено — правило без маршрут пак ще гръмне,
# както го иска ядрото (`stock.rule.route_id` е required=True).
MTO_OPTIONAL_CTX = "stock_mto_route_optional"

# Външният идентификатор на глобалния MTO маршрут — за съобщението в лога.
MTO_ROUTE_XMLID = "stock.route_warehouse0_mto"


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def create_resupply_routes(self, supplier_warehouses):
        """Call site 1 — ``stock/models/stock_warehouse.py`` (19.0, ред 718)."""
        # Флагът трябва да стигне до двата recordset-а: през `self` се взима
        # `self.env['stock.rule']`, а върху `supplier_warehouses` ядрото вика
        # `_get_global_route_rules_values()`.
        ctx = {MTO_OPTIONAL_CTX: True}
        return super(
            StockWarehouse, self.with_context(**ctx)
        ).create_resupply_routes(supplier_warehouses.with_context(**ctx))

    def _check_delivery_resupply(self, new_location, change_to_multiple):
        """Call site 2 — ``stock/models/stock_warehouse.py`` (19.0, ред 889)."""
        return super(
            StockWarehouse, self.with_context(**{MTO_OPTIONAL_CTX: True})
        )._check_delivery_resupply(new_location, change_to_multiple)

    def _get_global_route_rules_values(self):
        values = super()._get_global_route_rules_values()
        if self.env.context.get(MTO_OPTIONAL_CTX) and "mto_pull_id" not in values:
            # Ядрото изхвърля записа, когато `create_values['route_id']` е False
            # (изтрит MTO маршрут), но двата call site-а го индексират безусловно
            # и получават `TypeError: 'NoneType' object is not subscriptable`.
            # Връщаме празна обвивка: `_get_rule_values` ще произведе правило без
            # `route_id`, а `stock.rule.create` го отхвърля — точно каквото
            # коментарът в ядрото обещава („simply ignore the rule").
            _logger.warning(
                "Global route %s is missing - skipping the MTO rule for warehouse %s. "
                "Restore the route (odoo -u stock) to get MTO resupply rules back.",
                MTO_ROUTE_XMLID,
                self.display_name,
            )
            values = dict(
                values,
                mto_pull_id={
                    "depends": ["delivery_steps"],
                    "create_values": {},
                    "update_values": {},
                },
            )
        return values
