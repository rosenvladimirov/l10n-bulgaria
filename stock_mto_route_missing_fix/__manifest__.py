{
    "name": "Stock — Missing MTO Route Guard",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Inventory/Inventory",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "summary": "A deleted 'Replenish on Order (MTO)' route must not crash the "
               "warehouse form with a TypeError.",
    "description": """
Stock — Missing MTO Route Guard
===============================

``StockWarehouse._get_global_route_rules_values()`` deliberately drops a rule
whose route is gone::

    # `route_id` might be `False` if the user has deleted it, in such case we
    # should simply ignore the rule
    return {k: v for k, v in vals.items() if v.get('create_values', {}).get('route_id', True) and ...}

but two call sites then index the dropped key without checking::

    mto_vals = supplier_wh._get_global_route_rules_values().get('mto_pull_id')
    values = mto_vals['create_values']

* ``create_resupply_routes()`` — hit when a supplier warehouse delivering in
  one step (``ship_only``) is added to **Resupply From**.
* ``_check_delivery_resupply()`` — hit when the delivery steps of a warehouse
  that resupplies another one change to/from one step.

If the global route ``stock.route_warehouse0_mto`` has been deleted (record and
external ID both gone), both raise ``TypeError: 'NoneType' object is not
subscriptable`` and the warehouse can no longer be saved. Verified present in
18.0, 19.0 and 20.0.

This module does **not** reimplement the two methods — their bodies differ
between Odoo versions and copying them would silently freeze one version's
behaviour. Instead it wraps them with a context flag that is live only for the
duration of the guarded call, and under that flag:

* ``_get_global_route_rules_values()`` puts the dropped ``mto_pull_id`` key back
  as an empty envelope, so the unconditional subscript succeeds;
* ``stock.rule.create()`` discards rule values that carry no ``route_id`` —
  which is exactly and only the MTO rule that could not be routed.

The net effect is the behaviour the core comment promises: the MTO rule is
ignored, everything else (the inter-warehouse route and its pull rules) is
created as usual, and a warning naming the missing external ID lands in the log.

When the MTO route exists the module is a strict no-op: no key is ever
re-added, no rule is ever discarded.
""",
    "depends": [
        "stock",
    ],
    "data": [],
    "installable": True,
    # Дефектът блокира само конфигурацията на склад, не цялата сесия — затова
    # инсталацията остава ръчна.
    "auto_install": False,
    "application": False,
}
