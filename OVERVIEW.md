# l10n-bulgaria — Bulgaria Localization (Community Edition)

> Core open-source modules for Bulgarian Odoo 18 implementations.
> See [`OVERVIEW.bg.md`](OVERVIEW.bg.md) for the Bulgarian version.

## Scope

36 modules covering: central configuration, ЕКАТТЕ geography, NRA REST API, banking primitives, MT940 import, fiscal printers (ErpNet.FP), payment providers (Borica, myPOS), reports foundation, TARIC + AI classifier, HR holidays (61 leave types), multilanguage utilities, and small stock/sale extensions.

## License model

- **LGPL-3** — most modules (free for commercial use, weak copyleft)
- **AGPL-3** — some address/multilang utilities (network-copyleft, free)

All free and open-source. Production use does not require a paid license. Paid enterprise add-ons live in [`l10n-bulgaria-ee`](https://github.com/rosenvladimirov/l10n-bulgaria-ee).

## Module catalog (grouped by functional area)

### Foundation
- [`l10n_bg_config`](l10n_bg_config/README.md) — central configuration backbone, UIC validation, encryption, mixin architecture
- [`partner_multilang`](partner_multilang/) — JSONB multilingual partner names + transliteration
- [`l10n_bg_multilang`](l10n_bg_multilang/) — multi-language support for Partner/Company/Employee
- [`l10n_bg_address_extended`](l10n_bg_address_extended/) — precise BG address formatting
- [`markdown_viewer_locale`](markdown_viewer_locale/) — locale-aware Markdown viewer

### Geographic / Reference
- [`l10n_bg_city`](l10n_bg_city/) — ЕКАТТЕ database (28 regions, 265 municipalities, 5000+ settlements) + quarterly НСИ sync skeleton
- [`l10n_bg_tax_offices`](l10n_bg_tax_offices/) — NRA territorial directorate registry

### Accounting & Reports
- [`l10n_bg_reports_audit`](l10n_bg_reports_audit/README.md) — SQL views + NRA tag framework (technical base)
- [`l10n_bg_reports_config`](l10n_bg_reports_config/README.md) — configuration UI for accounting reports
- [`l10n_bg_report_theme`](l10n_bg_report_theme/) — section-based professional report layout
- [`l10n_bg_invoice_copy`](l10n_bg_invoice_copy/) — ОРИГИНАЛ/КОПИЕ watermark
- [`l10n_bg_invoice_grif`](l10n_bg_invoice_grif/) — Гриф field on invoice reports
- [`l10n_bg_report_stock`](l10n_bg_report_stock/) — accepted delivery documents
- [`l10n_bg_account_reconcile_patch`](l10n_bg_account_reconcile_patch/) — partner-name regexp_matches fix for JSONB

### Banking & Payments
- [`l10n_bg_bank_wallet`](l10n_bg_bank_wallet/) — PBKDF2+Fernet encrypted credential storage
- [`l10n_bg_account_statement_import_mt940`](l10n_bg_account_statement_import_mt940/) — MT940 import for BG banks
- [`payment_borica`](payment_borica/) — Borica APGW (CGI v4.0, EMV 3DS 2.x)
- [`payment_mypos`](payment_mypos/) — myPOS Checkout API (REST + 3DS)
- [`l10n_bg_infopay`](l10n_bg_infopay/README.md) — Borica InfoPay PSD2 core (statement sync, payments)

### NRA / Trade Registry / TARIC
- [`l10n_bg_api_nra`](l10n_bg_api_nra/) — NRA REST API core (OAuth 2.0, D1/D6/ETZ/VAT; NAP standalone app)
- [`l10n_bg_company_registry`](l10n_bg_company_registry/) — Trade Registry API (portal.registryagency.bg)
- [`l10n_bg_tariff_code`](l10n_bg_tariff_code/) — TARIC/HS/CN codes + EU API
- [`taric_ai_classifier`](taric_ai_classifier/) — AI-powered (Claude) automatic classification

### HR
- [`l10n_bg_hr_holidays`](l10n_bg_hr_holidays/) — 61 BG leave types per КТ + НЗОК; DOO treatment; chl. 37а notice; pro-rata helpers; annual leave schedule view
- [`l10n_bg_payroll_classifications`](l10n_bg_payroll_classifications/) — НКПД (occupational) + КИД (economic activity) classifications

### Fiscal Printers
- [`l10n_bg_erp_net_fp`](l10n_bg_erp_net_fp/) — ErpNet.FP integration
- [`l10n_bg_erp_net_fp_fleet`](l10n_bg_erp_net_fp_fleet/) — central fleet manager
- [`l10n_bg_erp_net_fp_iot_oca`](l10n_bg_erp_net_fp_iot_oca/) — OCA iot_oca bridge

### AI / Pipeline
- [`l10n_bg_ai_pipeline`](l10n_bg_ai_pipeline/) — pipeline stack with progressive-disclosure skills
- [`l10n_bg_claude_terminal`](l10n_bg_claude_terminal/) — Claude Code terminal + AI Tokenizer (Qdrant/Ollama)

### MRP / Multilang extensions
- [`l10n_bg_mrp_multilang`](l10n_bg_mrp_multilang/) — multi-language MRP workcenter names
- [`l10n_bg_project_multilang`](l10n_bg_project_multilang/) — multi-language project task fields
- [`hr_org_chart_multilang_fix`](hr_org_chart_multilang_fix/) — JSONB name resolution for hr_org_chart widget

### Stock / Sale extensions
- [`l10n_bg_sale_order_delivery_note`](l10n_bg_sale_order_delivery_note/) — delivery report for SO
- [`l10n_bg_stock_picking_comment_template`](l10n_bg_stock_picking_comment_template/) — comment-template repositioning
- [`l10n_bg_stock_sale_line_description`](l10n_bg_stock_sale_line_description/) — SO line description on pickings

## Installation order (suggested)

1. `l10n_bg_config`, `partner_multilang`, `l10n_bg_multilang`, `l10n_bg_address_extended`
2. `l10n_bg_city`, `l10n_bg_tax_offices`
3. `l10n_bg_report_theme`, `l10n_bg_reports_audit`, `l10n_bg_reports_config`
4. `l10n_bg_bank_wallet`, `l10n_bg_account_statement_import_mt940`
5. `l10n_bg_api_nra`, `l10n_bg_company_registry`, `l10n_bg_tariff_code`
6. `l10n_bg_hr_holidays`, `l10n_bg_payroll_classifications`
7. Specialized add-ons as needed (fiscal printers, payments, AI, stock/sale extensions)

## Per-module documentation

Each module has either a `README.md` (handwritten EN) + `README.bg.md` (handwritten BG), or auto-generated `README.en.md` + `README.bg.md` from manifest + source layout.

## Sister repositories

- [`l10n-bulgaria-oca`](https://github.com/OCA/l10n-bulgaria) — OCA-compatible mirrors
- [`l10n-bulgaria-ee`](https://github.com/rosenvladimirov/l10n-bulgaria-ee) — Enterprise add-ons (OPL-1, paid): full payroll, NRA decls, InfoPay, contract types
- [`l10n-bulgaria-expert`](https://github.com/rosenvladimirov/l10n-bulgaria-expert) — specialized expert modules (OPL-1)
- [`l10n-bulgaria-enterprise`](https://github.com/rosenvladimirov/l10n-bulgaria-enterprise) — Odoo Enterprise add-ons (OPL-1)

## Cross-repo ecosystem map

See [`claude.ai/L10N_BG_ECOSYSTEM.md`](https://github.com/rosenvladimirov/odoo-18.0/blob/main/claude.ai/L10N_BG_ECOSYSTEM.md) (if mirrored) or the consultant's working tree for the full functional grouping across all 5 repos.

## Contributing

Issues and PRs welcome via this repository's GitHub tracker.

## Maintainer

Rosen Vladimirov — Bulgarian Odoo developer & consultant, 11+ years on l10n_bg.
