<!-- /!\ Non OCA Context : badges point at the 19.0 branch. -->
[![Pre-commit Status](https://github.com/rosenvladimirov/l10n-bulgaria/actions/workflows/pre-commit.yml/badge.svg?branch=19.0)](https://github.com/rosenvladimirov/l10n-bulgaria/actions/workflows/pre-commit.yml?query=branch%3A19.0)
[![Build Status](https://github.com/rosenvladimirov/l10n-bulgaria/actions/workflows/test.yml/badge.svg?branch=19.0)](https://github.com/rosenvladimirov/l10n-bulgaria/actions/workflows/test.yml?query=branch%3A19.0)
[![codecov](https://codecov.io/gh/rosenvladimirov/l10n-bulgaria/branch/19.0/graph/badge.svg)](https://codecov.io/gh/rosenvladimirov/l10n-bulgaria)
[![Odoo](https://img.shields.io/badge/Odoo-19.0-714B67.svg)](https://github.com/rosenvladimirov/l10n-bulgaria/tree/19.0)
[![License](https://img.shields.io/badge/license-AGPL--3%20%2F%20LGPL--3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

# Bulgarian Localization for Odoo

**Community Bulgarian localization for Odoo 19.0 — the accounting, documents, payments, HR-data, waste-management and platform layer that Odoo's official `l10n_bg` modules leave out.**

Odoo's official Bulgarian localization ships **4 modules**. This repository adds **35 installable community modules** on top of them, covering areas the standard localization does not touch: chart-of-accounts configuration by economic sector (КИД), legal invoice layouts, periodic/manual inventory-cost accounting, MT940 bank-statement import, card payments, multilingual documents with transliteration, statutory waste-management reporting, and the platform tooling the rest of the stack builds on. It is maintained by the maintainer of the [OCA/l10n-bulgaria](https://github.com/OCA/l10n-bulgaria) project.

This repository is the **open-source community layer**. The regulatory reporting core — payroll, declarations to the National Revenue Agency (НАП) and the National Social Security Institute (НОИ), SAF-T, annual financial statements (ГФО) and Intrastat — is delivered as a separately licensed commercial extension (see [Commercial extension](#commercial-extension)).

## Regulatory coverage

The tone below is factual: an empty cell means that layer does not cover the obligation. Community modules named in a cell live in this repository; a check in the *Commercial* column points to the separately licensed extension.

| Obligation | Legal basis | Odoo standard | This repository (community) | Commercial |
|---|---|---|---|---|
| Chart of accounts & tax setup | Accountancy Act (ЗСч); VAT Act (ЗДДС) | `l10n_bg` (official) | `l10n_bg_config` + КИД industry packs | |
| Legal invoice layout (original / copy) | VAT Act (ЗДДС) art. 114 | | `l10n_bg_invoice_grif`, `l10n_bg_invoice_copy` | |
| Inventory valuation & auto journal entries | Accountancy Act (ЗСч) | partial (`stock_account`) | `l10n_bg_stock_account` | |
| Accepted-delivery / goods documents | Accountancy Act (ЗСч) art. 6 | | `l10n_bg_report_stock` and helpers | |
| Bank statement import (MT940) | — | OCA generic | `l10n_bg_account_statement_import_mt940` | |
| Card payments (myPOS) | PSD2 | payment framework | `payment_mypos`, `payment_mypos_embedded` | |
| Waste-management reporting | Waste Management Act (ЗУО); Ordinance № 2/2014 | | `l10n_bg_waste_*` (Annex 4 / 8 / 18) | |
| VAT return & sales/purchase ledgers | VAT Act (ЗДДС) art. 125; ППЗДДС | | | ✓ (NRA e-filing) |
| VIES / EC sales & acquisitions | VAT Act (ЗДДС); EU regulation | `base_vat` (number check) | | ✓ |
| Intrastat | EU Reg. 638/2004 | | | ✓ |
| Payroll, social security & PIT | Labour Code (КТ); Social Security Code (КСО); PITA (ЗДДФЛ) | | HR-version data (`l10n_bg_hr`) | ✓ (full payroll) |
| NRA declarations Обр. 1 / Обр. 6, labour-contract register (ЕТЗ) | Ordinance Н-13; Labour Code art. 62 | | | ✓ |
| NSSI (НОИ) benefit declarations | Social Security Code (КСО) | | | ✓ |
| Annual financial statements (ГФО) | Accountancy Act (ЗСч); Commerce Act (ТЗ) | | | ✓ |
| SAF-T | phased obligation (from 2026) | | | in preparation |

## Available addons

All modules below are installable on the `19.0` branch. Each module declares its own license in its `__manifest__.py`; see [Author and license](#author-and-license).

### Accounting & invoicing

| Module | Version | Summary |
|---|---|---|
| `l10n_bg_config` | 19.0.8.6.10 | Central localization configuration — chart-of-accounts install filter, UIC validation, active КИД sector, shared mixins |
| `l10n_bg_config_plugins_industry_map` | 19.0.1.0.4 | Account ↔ КИД industry-mapping seed data (НСИ methodology) |
| `l10n_bg_config_plugins_industry_agriculture` | 19.0.1.0.0 | КИД sector A preset (Agriculture, Forestry & Fishing) for the CoA install filter |
| `l10n_bg_config_plugins_industry_construction` | 19.0.1.0.0 | КИД sector F preset (Construction) |
| `l10n_bg_config_plugins_industry_manufacturing` | 19.0.1.0.0 | КИД sector C preset (Manufacturing) |
| `l10n_bg_config_plugins_industry_nonprofit` | 19.0.1.0.0 | КИД sector S preset (Non-profit / ЮЛНЦ) |
| `l10n_bg_invoice_grif` | 19.0.1.0.0 | Adds an ОРИГИНАЛ / КОПИЕ (Гриф) field to invoice reports |
| `l10n_bg_invoice_copy` | 19.0.1.0.0 | COPY watermark on Bulgarian invoice reports |
| `l10n_bg_account_statement_import_mt940` | 19.0.1.0.0 | Import bank statements in the MT940 format used by Bulgarian banks |

### Inventory accounting & delivery documents

| Module | Version | Summary |
|---|---|---|
| `l10n_bg_stock_account` | 19.0.1.5.0 | Auto-post journal entries at picking validation for manual / periodic costing |
| `l10n_bg_stock_account_manual` | 19.0.1.0.0 | End-user documentation for Stock Auto Accounting, shown via the Markdown Viewer |
| `l10n_bg_report_stock` | 19.0.1.0.0 | Accepted-delivery (стокова разписка) documents on stock pickings |
| `l10n_bg_stock_picking_comment_template` | 19.0.1.0.0 | Positions `base_comment_template` top/bottom blocks on the delivery slip |
| `l10n_bg_stock_sale_line_description` | 19.0.1.0.0 | Show the sale-order-line description on pickings and delivery slips |

### Waste management (ЗУО / Ordinance № 2/2014)

| Module | Version | Summary |
|---|---|---|
| `l10n_bg_waste_base` | 19.0.1.0.0 | Waste classification catalog, treatment activities and treatment sites |
| `l10n_bg_waste_permit` | 19.0.1.0.0 | Treatment permits with annual quotas and real-time usage tracking |
| `l10n_bg_waste_picking` | 19.0.1.0.0 | Capture waste codes at picking validation, enforce quota, trace lots to incoming pickings |
| `l10n_bg_waste_report` | 19.0.1.0.0 | XLSX monthly report (Annex 4), annual skeleton (Annex 18), PDF identification document (Annex 8) |

### Payments

| Module | Version | Summary |
|---|---|---|
| `payment_mypos` | 19.0.2.0.0 | Accept card payments via the myPOS Checkout API (REST + 3DS) |
| `payment_mypos_embedded` | 19.0.1.0.0 | On-site iFrame myPOS checkout (no redirect) |

### HR & personnel

| Module | Version | Summary |
|---|---|---|
| `l10n_bg_hr` | 19.0.2.0.4 | HR Version extension — work-location address and contract amendments |
| `hr_org_chart_multilang_fix` | 19.0.1.0.0 | Resolve translatable JSONB employee names before the org-chart widget renders them |

### Reference data & multilingual

| Module | Version | Summary |
|---|---|---|
| `partner_multilang` | 19.0.2.0.2 | Multilingual partner names with automatic transliteration and language detection |
| `l10n_bg_address_extended` | 19.0.1.0.1 | Bulgarian extended address fields and formatting |
| `markdown_viewer_locale` | 19.0.3.0.4 | View localized Markdown documents based on the user's language |
| `dict_str_patch` | 19.0.1.0.0 | Monkey-patch `dict` with the public `str` methods needed by translated JSONB fields |

### Setup & onboarding

| Module | Version | Summary |
|---|---|---|
| `l10n_bg_db_installer` | 19.0.1.4.0 | Bulgaria fields on the database manager + guided localization setup on a new database |
| `l10n_bg_onboarding` | 19.0.1.3.0 | Full-screen animated guided setup on first login of a fresh Bulgarian database |

### Platform & infrastructure

| Module | Version | Summary |
|---|---|---|
| `l10n_bg_live_refresh` | 19.0.2.7.1 | Generic bus channel + OWL patches that live-reload and flash backend Form/List views |
| `l10n_bg_queue_poll` | 19.0.1.2.0 | `queue_job` engine that polls a model method with adaptive backoff, then live-refreshes |
| `l10n_bg_claude_terminal` | 19.0.1.40.0 | Claude Code terminal + AI Tokenizer (Qdrant / Ollama) MCP stack |
| `l10n_bg_ai_pipeline` | 19.0.1.2.0 | Skills engine — progressive disclosure, semantic matching and dynamic step injection |
| `l10n_bg_ai_accounting_glue` | 19.0.1.0.0 | Bulgarian accounting / MRP AI skills (knowledge-only) for the pipeline — **OPL-1** |
| `l10n_bg_discuss_proxy` | 19.0.1.3.0 | Publish internal Discuss messages to a Centrifugo proxy for external listeners |
| `l10n_bg_telegram_agent` | 19.0.2.0.0 | Bridge Telegram chats into Odoo Discuss (Centrifugo consumer + AI responder) |

## Installation

1. **Requirements.** Odoo 19.0 (Community or Enterprise) and the official Odoo Bulgarian localization (`l10n_bg` and its companion modules), which several modules here depend on.

2. **OCA dependencies.** Some modules depend on published OCA add-ons. Add the relevant OCA repositories to your `addons_path` alongside this one:
   - `queue_job` — [OCA/queue](https://github.com/OCA/queue) — for `l10n_bg_queue_poll`
   - `account_statement_import_file` — [OCA/account-statement-import](https://github.com/OCA/account-statement-import) — for the MT940 importer
   - `report_xlsx` — [OCA/reporting-engine](https://github.com/OCA/reporting-engine) — for the waste XLSX report
   - `base_comment_template`, `stock_picking_comment_template` — [OCA/reporting-engine](https://github.com/OCA/reporting-engine) / [OCA/stock-logistics-reporting](https://github.com/OCA/stock-logistics-reporting) — for the picking comment module

3. **Clone the branch** into a directory on your Odoo `addons_path`:
   ```bash
   git clone -b 19.0 https://github.com/rosenvladimirov/l10n-bulgaria.git
   ```

4. **Register the path** in your Odoo configuration:
   ```ini
   # odoo.conf
   addons_path = /opt/odoo/odoo/addons,/opt/odoo/l10n-bulgaria,/opt/odoo/OCA/queue,/opt/odoo/OCA/account-statement-import,/opt/odoo/OCA/reporting-engine
   ```

5. **Install** the modules you need (dependencies are pulled in automatically):
   ```bash
   odoo -d your_db -i l10n_bg_config --stop-after-init
   ```
   Start from `l10n_bg_config`, then add domain modules (`l10n_bg_stock_account`, `l10n_bg_waste_base`, `payment_mypos`, …) as required. On a fresh database, `l10n_bg_onboarding` walks you through the initial setup.

6. **Upgrade** after pulling new commits:
   ```bash
   odoo -d your_db -u l10n_bg_config --stop-after-init
   ```

## Versions and roadmap

| Branch | Status | Notes |
|---|---|---|
| `18.0` | Maintenance | Prior production line; still receiving fixes. Includes `payment_borica` and `taric_ai_classifier`, which are not yet ported to 19.0. |
| `19.0` | **Current — production** | The branch documented here; recommended for new deployments. |
| `20.0` | In preparation | Early preview branch tracking Odoo 20.0. Not production-ready and carries no readiness commitment. |

**Honest porting note.** The `19.0` branch is the active production line, but the port from `18.0` is not one-to-one. In particular `payment_borica` (Borica APGW) and `taric_ai_classifier` (AI TARIC classification) are present on `18.0` and have **not yet been ported** to `19.0`. Regulatory-reporting modules that once lived alongside the community layer are now consolidated into the commercial extension. If you depend on a module you do not see on `19.0`, please open an issue.

## Commercial extension

A commercial extension exists and covers the **statutory reporting core** that Bulgarian companies are legally required to file:

- **Payroll (ТРЗ)** — full payroll with ДОО / ЗО / УПФ / ТЗПБ, personal income tax (ДДФЛ) and minimum-insurance-income (МОД) handling, plus the non-employment regimes (civil, management and self-insured contracts).
- **Declarations to the National Revenue Agency (НАП)** — VAT return and sales/purchase ledgers, Декларация Обр. 1 / Обр. 6, the electronic labour-contract register (ЕТЗ), and e-filing over the NRA API.
- **Declarations to the National Social Security Institute (НОИ)** — sickness and benefit forms.
- **SAF-T** — the phased Standard Audit File for Tax obligation.
- **Annual financial statements (ГФО)** — NSI-format statements via the accounting-report engine.
- **Intrastat** — arrivals/dispatches XML declarations.

This layer is published and licensed by **Terraros Commerce Ltd. (Терарос Комерс ЕООД)** under OPL-1. Access, licensing and support are arranged directly with the publisher — open an issue on this repository or contact the maintainer via [github.com/rosenvladimirov](https://github.com/rosenvladimirov). No pricing is published here.

## Author and license

- **Author and domain expert:** Rosen Vladimirov — maintainer of [OCA/l10n-bulgaria](https://github.com/OCA/l10n-bulgaria).
- **Rights holder:** Terraros Commerce Ltd. (Терарос Комерс ЕООД).

Every module declares its own license in its `__manifest__.py`. In this repository:

- **AGPL-3** and **LGPL-3** cover the community modules — they are free and open source.
- **OPL-1** applies to a single module, `l10n_bg_ai_accounting_glue`, which packages commercially licensed AI skill/knowledge content on top of the (LGPL-3) pipeline engine.

The separately maintained commercial extension (see above) is licensed under **OPL-1**.

## Contributing

Issues and pull requests are welcome on the [rosenvladimirov/l10n-bulgaria](https://github.com/rosenvladimirov/l10n-bulgaria) tracker. Please target the `19.0` branch for current work and follow the Odoo/OCA coding and review guidelines.

Community variants of several modules are also maintained under the OCA umbrella at [OCA/l10n-bulgaria](https://github.com/OCA/l10n-bulgaria); where a module exists in both places, contributions are coordinated across the two.

User-facing strings, module manifests and this README are kept in **English** (a Bulgarian `README.bg.md` is maintained separately); translations are contributed through the `i18n/*.po` files, not by editing source strings.
