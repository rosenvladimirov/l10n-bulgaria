# l10n_bg_waste_report

**License:** AGPL-3.0
**Target Odoo:** 19.0
**Depends:** `l10n_bg_waste_picking`, `report_xlsx` (OCA `reporting-engine`)

Regulatory reports for the Bulgarian waste management stack.

| Report | Annex | Output | Wizard |
|---|---|---|---|
| Monthly bookkeeping | Прил. №4 of Наредба №1/2014 | XLSX (4 sheets: I Received · II Treated · III Generated · IV Delivered + Header) | `l10n.bg.waste.monthly.report.wizard` |
| Annual report | Прил. №18 | XLSX (skeleton — SUM by code × activity per year) | `l10n.bg.waste.annual.report.wizard` |
| ID document for hazardous waste transport | Прил. №8 | QWeb-PDF (3 sections + signature blocks) | binding on `l10n.bg.waste.id.document` |

## Generation flow

1. Open *Waste Management → Reports → Annex 4 — Monthly*.
2. Pick a site + period (year + month) + optional code filter.
3. Optional: pick a partner (consultant) — XLSX is generated and download
   is offered; mailing the file to the consultant is a TODO for v2.

## Sections in the monthly XLSX

- **Header** — company, VAT/EIK, site, EKATTE, RIOSV, period (10 rows).
- **I. Received** — for each incoming picking with waste lines on the
  site: date · code · description · sender · sender VAT · transport doc · ton.
- **II. Treated** — skeleton; v1 leaves empty. v2 will derive from
  `mrp.production` consumption of waste-flagged lots.
- **III. Generated** — skeleton; v1 leaves empty. v2 from MO output side.
- **IV. Delivered** — for each outgoing picking with waste lines on the
  site: date · code · receiver · receiver VAT · transport doc · ton.

## Notes

- Annex 8 PDF binds to the `l10n.bg.waste.id.document` model so the
  *Print* button auto-appears on the form view.
- The XLSX styling uses the same Ink & Rose palette as the application
  icon — `#1F3D44` for section headers and `#8FA89E` for column heads.
- Annex 18 SUM groups by `c.code, c.name` and filters by warehouse to
  match the site → warehouse linkage from `l10n_bg_waste_base`.

## Roadmap

- **v2** — automatic submission to НИСО (НИСО has no public API at
  2026-05; revisit when published).
- **v2** — populate sections II + III from `mrp.production` records that
  consume waste-tagged lots.
- **v2** — email delivery of the XLSX to a configured consultant when
  the wizard's `recipient_partner_id` is set.
