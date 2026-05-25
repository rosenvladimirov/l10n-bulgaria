# l10n_bg_waste_permit

**License:** AGPL-3.0
**Target Odoo:** 19.0
**Depends:** `l10n_bg_waste_base`, `mail`

Bulgarian waste treatment permits and quotas with real-time usage tracking.

## Models

| Model | Purpose |
|---|---|
| `l10n.bg.waste.permit` | Header record per permit (RD-XX-NNN / КР-NN) — number, dates, authority, draft/active/suspended/expired/revoked workflow. |
| `l10n.bg.waste.permit.line` | One quota row per (site × waste code × activity) with annual quota, on-site storage limit and live computed usage. |

## Online quota compute

`l10n.bg.waste.permit.line._compute_usage` runs a single SQL aggregation
on `stock.move.line` filtered by:

- `waste_code_id` matches the permit line
- `state = 'done'`
- the move's destination location belongs to a warehouse linked to the
  permit line's site (via `l10n_bg_waste_site_warehouse_rel`)
- the picking's `date_done` is within the current calendar year

It returns four computed fields: `quota_used_ytd_kg`,
`quota_remaining_kg`, `quota_percent_used`, `current_storage_kg`.

When `l10n_bg_waste_picking` is **not installed** (the
`waste_code_id`/`waste_quantity_kg` columns on `stock.move.line` do not
exist), the compute degrades gracefully and returns zeros — the permit
module is therefore usable standalone for permit/quota administration
without committing to stock integration.

## Workflow & lifecycle

- **draft** → **active** — requires at least one quota line.
- **active** → **suspended** | **revoked** — manual transitions with mail tracking.
- A daily cron (`cron_waste_permit_expiry`) auto-moves active permits to
  **expired** when `date_valid_to < today` and posts a chatter note.

## Security

Reuses the three groups defined in `l10n_bg_waste_base`:
`group_waste_user` reads, `group_waste_manager` manages permits & lines,
`group_waste_admin` inherits both plus base.group_system.
