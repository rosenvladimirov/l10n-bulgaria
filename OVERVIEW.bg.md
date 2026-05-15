# l10n-bulgaria — Българска локализация (Community Edition)

> Основни open-source модули за внедряване на българската локализация в Odoo 18.

## Обхват

36 модула, които покриват: централна конфигурация, ЕКАТТЕ географска база, REST API към НАП, банкови помощници, MT940 импорт, фискални принтери (ErpNet.FP), картови платежни доставчици (Borica, myPOS), фундамент за отчети, TARIC + AI класификатор, отпуски по КТ (61 типа), многоезични помощници и малки разширения за stock/sale.

## Лицензен модел

- **LGPL-3** — повечето модули (свободно за комерсиална употреба, слабо copyleft)
- **AGPL-3** — някои address/multilang помощници (network-copyleft, безплатно)

Всичко е безплатно и open-source. Production употреба не изисква платен лиценз. Платените enterprise add-ons са в [`l10n-bulgaria-ee`](https://github.com/rosenvladimirov/l10n-bulgaria-ee).

## Каталог на модулите (по функционални групи)

### Основа
- [`l10n_bg_config`](l10n_bg_config/README.md) — централна конфигурация, BULSTAT/ЕИК валидация, криптиране, mixin архитектура
- [`partner_multilang`](partner_multilang/) — JSONB многоезични имена на партньори + транслитерация
- [`l10n_bg_multilang`](l10n_bg_multilang/) — многоезична поддръжка за Partner/Company/Employee
- [`l10n_bg_address_extended`](l10n_bg_address_extended/) — прецизно форматиране на български адреси
- [`markdown_viewer_locale`](markdown_viewer_locale/) — преглед на локализирани Markdown файлове

### Географски / Референтни данни
- [`l10n_bg_city`](l10n_bg_city/) — ЕКАТТЕ база (28 области, 265 общини, 5000+ населени места) + тримесечен sync с НСИ
- [`l10n_bg_tax_offices`](l10n_bg_tax_offices/) — териториални дирекции на НАП

### Счетоводство & Отчети
- [`l10n_bg_reports_audit`](l10n_bg_reports_audit/README.md) — SQL views + НАП tag framework (технически фундамент)
- [`l10n_bg_reports_config`](l10n_bg_reports_config/README.md) — UI конфигурация на счетоводни отчети
- [`l10n_bg_report_theme`](l10n_bg_report_theme/) — section-based корпоративен report theme
- [`l10n_bg_invoice_copy`](l10n_bg_invoice_copy/) — воден знак ОРИГИНАЛ/КОПИЕ
- [`l10n_bg_invoice_grif`](l10n_bg_invoice_grif/) — поле „Гриф“ на фактурите
- [`l10n_bg_report_stock`](l10n_bg_report_stock/) — приемно-предавателни документи
- [`l10n_bg_account_reconcile_patch`](l10n_bg_account_reconcile_patch/) — поправка за JSONB partner име в regexp_matches

### Банкови & Платежни
- [`l10n_bg_bank_wallet`](l10n_bg_bank_wallet/) — PBKDF2+Fernet криптиран storage
- [`l10n_bg_account_statement_import_mt940`](l10n_bg_account_statement_import_mt940/) — MT940 импорт за БГ банки
- [`payment_borica`](payment_borica/) — Borica APGW (CGI v4.0, EMV 3DS 2.x)
- [`payment_mypos`](payment_mypos/) — myPOS Checkout API (REST + 3DS)
- [`l10n_bg_infopay`](l10n_bg_infopay/README.md) — Borica InfoPay PSD2 ядро (синхронизация на извлечения, плащания)

### НАП / Търговски регистър / TARIC
- [`l10n_bg_api_nra`](l10n_bg_api_nra/) — REST API ядро за НАП (OAuth 2.0, Д1/Д6/ETZ/ДДС; NAP standalone app)
- [`l10n_bg_company_registry`](l10n_bg_company_registry/) — API на Търговския регистър (portal.registryagency.bg)
- [`l10n_bg_tariff_code`](l10n_bg_tariff_code/) — TARIC/HS/CN кодове + EU API
- [`taric_ai_classifier`](taric_ai_classifier/) — AI-базиран (Claude) автоматичен класификатор

### Личен състав
- [`l10n_bg_hr_holidays`](l10n_bg_hr_holidays/) — 61 БГ типа отпуски по КТ + НЗОК; DOO третиране; уведомление по чл. 37а НРВПО; pro-rata помощници; годишен график (Phase 5.1)
- [`l10n_bg_payroll_classifications`](l10n_bg_payroll_classifications/) — НКПД (професии) + КИД (икономически дейности)

### Фискални принтери
- [`l10n_bg_erp_net_fp`](l10n_bg_erp_net_fp/) — ErpNet.FP интеграция
- [`l10n_bg_erp_net_fp_fleet`](l10n_bg_erp_net_fp_fleet/) — централен fleet manager
- [`l10n_bg_erp_net_fp_iot_oca`](l10n_bg_erp_net_fp_iot_oca/) — OCA iot_oca bridge

### AI / Pipeline
- [`l10n_bg_ai_pipeline`](l10n_bg_ai_pipeline/) — pipeline стек със скилове (progressive disclosure)
- [`l10n_bg_claude_terminal`](l10n_bg_claude_terminal/) — Claude Code терминал + AI Tokenizer (Qdrant/Ollama)

### MRP / Многоезични разширения
- [`l10n_bg_mrp_multilang`](l10n_bg_mrp_multilang/) — многоезични имена на работни центрове (MRP)
- [`l10n_bg_project_multilang`](l10n_bg_project_multilang/) — многоезични полета за project tasks
- [`hr_org_chart_multilang_fix`](hr_org_chart_multilang_fix/) — JSONB имена за hr_org_chart widget

### Stock / Sale разширения
- [`l10n_bg_sale_order_delivery_note`](l10n_bg_sale_order_delivery_note/) — приемно-предавателен отчет за SO
- [`l10n_bg_stock_picking_comment_template`](l10n_bg_stock_picking_comment_template/) — препозициониране на comment-template блокове
- [`l10n_bg_stock_sale_line_description`](l10n_bg_stock_sale_line_description/) — SO line description в pickings

## Препоръчителен ред на инсталация

1. `l10n_bg_config`, `partner_multilang`, `l10n_bg_multilang`, `l10n_bg_address_extended`
2. `l10n_bg_city`, `l10n_bg_tax_offices`
3. `l10n_bg_report_theme`, `l10n_bg_reports_audit`, `l10n_bg_reports_config`
4. `l10n_bg_bank_wallet`, `l10n_bg_account_statement_import_mt940`
5. `l10n_bg_api_nra`, `l10n_bg_company_registry`, `l10n_bg_tariff_code`
6. `l10n_bg_hr_holidays`, `l10n_bg_payroll_classifications`
7. Специализирани add-ons по нужда (фискални принтери, плащания, AI, stock/sale)

## Документация на модул

Всеки модул има или `README.md` (ръчно EN) + `README.bg.md` (ръчно BG), или авто-генерирани `README.en.md` + `README.bg.md` от manifest + source layout.

## Свързани репозитори

- [`l10n-bulgaria-oca`](https://github.com/OCA/l10n-bulgaria) — OCA-съвместими mirrors
- [`l10n-bulgaria-ee`](https://github.com/rosenvladimirov/l10n-bulgaria-ee) — Enterprise add-ons (OPL-1, платени): пълна ТРЗ, НАП декларации, InfoPay, типове договори
- [`l10n-bulgaria-expert`](https://github.com/rosenvladimirov/l10n-bulgaria-expert) — специализирани expert модули (OPL-1)
- [`l10n-bulgaria-enterprise`](https://github.com/rosenvladimirov/l10n-bulgaria-enterprise) — Odoo Enterprise add-ons (OPL-1)

## Cross-repo ecosystem карта

Виж [`claude.ai/L10N_BG_ECOSYSTEM.md`](https://github.com/rosenvladimirov/odoo-18.0/blob/main/claude.ai/L10N_BG_ECOSYSTEM.md) (ако е mirror-нат) или работното дърво на консултанта за пълно функционално групиране в 5-те repos.

## Принос

Issues и PRs добре дошли през GitHub tracker-а на това репозитори.

## Maintainer

Росен Владимиров — български Odoo developer & консултант, 11+ години работа върху l10n_bg.
