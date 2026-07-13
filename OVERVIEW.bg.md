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
- [`l10n_bg_address_extended`](l10n_bg_address_extended/) — прецизно форматиране на български адреси
- [`markdown_viewer_locale`](markdown_viewer_locale/) — преглед на локализирани Markdown файлове

### Географски / Референтни данни

### Счетоводство & Отчети
- [`l10n_bg_invoice_copy`](l10n_bg_invoice_copy/) — воден знак ОРИГИНАЛ/КОПИЕ
- [`l10n_bg_invoice_grif`](l10n_bg_invoice_grif/) — поле „Гриф“ на фактурите
- [`l10n_bg_report_stock`](l10n_bg_report_stock/) — приемно-предавателни документи
- [`l10n_bg_account_reconcile_patch`](l10n_bg_account_reconcile_patch/) — поправка за JSONB partner име в regexp_matches

### Банкови & Платежни
- [`l10n_bg_account_statement_import_mt940`](l10n_bg_account_statement_import_mt940/) — MT940 импорт за БГ банки
- [`payment_borica`](payment_borica/) — Borica APGW (CGI v4.0, EMV 3DS 2.x)
- [`payment_mypos`](payment_mypos/) — myPOS Checkout API (REST + 3DS)

### НАП / Търговски регистър / TARIC
- [`taric_ai_classifier`](taric_ai_classifier/) — AI-базиран (Claude) автоматичен класификатор

### Личен състав

### Фискални принтери

### AI / Pipeline
- [`l10n_bg_ai_pipeline`](l10n_bg_ai_pipeline/) — pipeline стек със скилове (progressive disclosure)
- [`l10n_bg_claude_terminal`](l10n_bg_claude_terminal/) — Claude Code терминал + AI Tokenizer (Qdrant/Ollama)

### MRP / Многоезични разширения
- [`hr_org_chart_multilang_fix`](hr_org_chart_multilang_fix/) — JSONB имена за hr_org_chart widget

### Stock / Sale разширения
- [`l10n_bg_stock_picking_comment_template`](l10n_bg_stock_picking_comment_template/) — препозициониране на comment-template блокове
- [`l10n_bg_stock_sale_line_description`](l10n_bg_stock_sale_line_description/) — SO line description в pickings

## Препоръчителен ред на инсталация

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
