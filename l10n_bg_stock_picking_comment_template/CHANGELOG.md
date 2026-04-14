# Changelog

All notable changes to the l10n_bg_stock_picking_comment_template module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [19.0.1.0.0] - 2026-04-10

### Added
- Initial 19.0 port. Pure view-only bridge module on top of OCA `stock_picking_comment_template` (which wires the `comment.template` mixin into `stock.picking`, the Comments tab on the picking form, and the Settings menu).
- In 19.0, `l10n_bg_report_stock.report_accepted_delivery_document` is a standalone QWeb template (not an inherit of `stock.report_delivery_document`), so the OCA inherit does not affect the Bulgarian report. This module inherits the Bulgarian template directly and inserts top/bottom comment blocks at positions tailored for the report — top after `<div id='informations'>`, bottom before `<div name='signature'>`. No render guard is needed because the inherit only applies to the Bulgarian template.
- Note: 19.0 has no handover protocol report yet (only the accepted delivery slip), so unlike the 18.0 version this module wires only one report.
