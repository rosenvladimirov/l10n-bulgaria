# Stock — Missing MTO Route Guard

> A deleted "Replenish on Order (MTO)" route must not break the warehouse form
> with `TypeError: 'NoneType' object is not subscriptable`.

**Module:** `stock_mto_route_missing_fix` | **Version:** 19.0.1.0.0 | **License:** AGPL-3 | **Category:** Inventory

## The defect

`StockWarehouse._get_global_route_rules_values()` deliberately drops a rule
whose route is gone:

```python
# `route_id` might be `False` if the user has deleted it, in such case we
# should simply ignore the rule
return {k: v for k, v in vals.items() if v.get('create_values', {}).get('route_id', True) and ...}
```

Two call sites then index the dropped key unconditionally:

```python
mto_vals = supplier_wh._get_global_route_rules_values().get('mto_pull_id')
values = mto_vals['create_values']
```

| # | Method | Reached when |
|---|---|---|
| 1 | `create_resupply_routes()` | a supplier warehouse delivering in one step (`ship_only`) is added to **Resupply From** |
| 2 | `_check_delivery_resupply()` | the delivery steps of a warehouse that resupplies another one change to/from one step |

With `stock.route_warehouse0_mto` deleted (record and external ID both gone),
both raise `TypeError` and the warehouse can no longer be saved. Verified
present in 18.0, 19.0 and 20.0.

## The guard

The module does **not** reimplement the two methods — their bodies differ across
Odoo versions and a copy would silently freeze one version's behaviour. It wraps
them with a context flag that is live only for the duration of the guarded call,
and under that flag:

- `_get_global_route_rules_values()` puts the dropped `mto_pull_id` key back as
  an empty envelope, so the unconditional subscript succeeds;
- `stock.rule.create()` discards rule values carrying no `route_id` — which is
  exactly and only the MTO rule that could not be routed.

Net effect: the behaviour the core comment promises. The MTO rule is ignored,
the inter-warehouse route and its pull rules are created as usual, and a warning
naming the missing external ID is logged.

With the MTO route in place the module is a strict no-op.

## Restoring the route

The guard keeps the system usable; it does not restore the route.

```sql
SELECT id, name->>'en_US' AS name_en, active, company_id FROM stock_route ORDER BY id;
SELECT * FROM ir_model_data WHERE module='stock' AND name='route_warehouse0_mto';
```

- **No such row** → `odoo -d <db> -u stock --stop-after-init` recreates it
  (`noupdate="1"` blocks overwriting, not creating a missing external ID).
- **Route present but external ID gone** (renamed) → do not run `-u stock`, it
  would create a duplicate; restore the `ir_model_data` row instead.

## Tests

`odoo -d <db> -i stock_mto_route_missing_fix --test-enable --stop-after-init`
