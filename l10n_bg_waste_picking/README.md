# l10n_bg_waste_picking

**License:** AGPL-3.0
**Target Odoo:** 19.0
**Depends:** `l10n_bg_waste_permit`, `stock`

Stock-integration layer of the Bulgarian waste management stack.

## What it does

- Marks `product.template` records as waste with `is_waste_product` + optional default code.
- Marks `stock.picking.type` records as waste intake with default R/D activity.
- Extends `stock.picking` with `waste_site_id`, `waste_permit_id`, `waste_transport_doc`, `waste_vehicle_plate`, `waste_id_document_id`.
- Extends `stock.move.line` with `waste_code_id`, `waste_quantity_kg` (UoM-converted) and `waste_origin_partner_id`.
- Extends `stock.lot` with `waste_code_id` + `waste_source_picking_ids` (M2M back to incoming pickings) — enables traceability of recycled output to source shipments.
- Provides `l10n.bg.waste.id.document` — Annex 8 of Наредба №1/2014 (hazardous waste transport ID document).

## Validation flow

```
[Validate] on incoming picking
        │
        ▼
button_validate hook
        │
        ├── waste lines missing code → open wizard (require codes)
        │
        ├── quota usage will hit >100% → open wizard with block + require note
        │
        ├── quota usage will hit >80% (but <100%) → open wizard with warning + decision
        │
        └── all good → super().button_validate()
```

The wizard (`l10n.bg.waste.code.wizard`) is the single entry-point for
all three branches and re-enters `button_validate` with a context flag
that skips the gate once the user has either:

- supplied missing codes, or
- chosen *Proceed* with a written justification when over-quota.

The chatter receives a structured summary on each acceptance, and the
company-level waste manager (`res.company.waste_manager_id`) gets an
`activity_schedule` warning when the quota is breached.

## Notes for Odoo 19

- `stock.move.line.quantity` is the modern field (the legacy `qty_done`
  was removed in 18.0+). Conversion to kilograms uses
  `product_uom_id._compute_quantity(quantity, kg)`.
- All SQL aggregations honour `stock_picking.date_done` and
  `stock_move_line.state = 'done'`.
- Pickings with `state = 'done'` continue to expose the waste lines for
  reporting — no destructive changes to the move line records.
