# Changelog

All notable changes to the l10n_bg_stock_picking_comment_template module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.1.0.0] - 2026-04-10

### Added
- Initial release. Pure view-only bridge module on top of OCA `stock_picking_comment_template` (which already wires the `comment.template` mixin into `stock.picking`, the Comments tab on the picking form, and the Settings menu).
- Deactivates the OCA inherit `stock_picking_comment_template.report_delivery_document_comments`, which inserts top/bottom comments at positions unsuitable for the Bulgarian protocols (top before `stock_move_table`, bottom after `web.external_layout`, i.e. outside the page layout).
- Re-injects top/bottom comment blocks on `stock.report_delivery_document` at positions tailored for the Bulgarian reports (top after `<div id='informations'>`, bottom before `<div name='signature'>`), gated by the existing Bulgarian render guards `is_handover_protocol` and `l10n_bg_report_stock_accepted` so the standard `stock.report_deliveryslip` is not affected.
