# Changelog

All notable changes to `stock_mto_route_missing_fix` will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Odoo module versioning
(`<odoo-major>.<odoo-minor>.<feature>.<fix>.<patch>`).

## [18.0.1.0.0] - 2026-09-01

### Added
- Initial release.
- Guard both core call sites that subscript the `mto_pull_id` entry dropped by
  `StockWarehouse._get_global_route_rules_values()` when the global route
  `stock.route_warehouse0_mto` has been deleted:
  `create_resupply_routes()` (adding a `ship_only` supplier warehouse to
  *Resupply From*) and `_check_delivery_resupply()` (changing delivery steps of
  a resupplying warehouse). Both raised
  `TypeError: 'NoneType' object is not subscriptable`.
- Guard implemented without copying the core method bodies: a context flag,
  live only for the guarded call, restores the dropped key as an empty envelope
  and makes `stock.rule.create()` discard the resulting route-less rule, with a
  warning naming the missing external ID.
- Tests covering both call sites with the MTO route deleted.
