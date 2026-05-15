# Account Statement Import Mt940

> MT940 банкови извлечения — БГ банки

**Модул:** `l10n_bg_account_statement_import_mt940` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** ?

## Описание

MT940 банкови извлечения — БГ банки

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `account_statement_import_file` | — |

**Python пакети:** `mt-940`

## Разширени модели

- `account.journal` (extension)

## Помощници (wizards)

- `wizard/account_statement_import.py`
- `wizard/bank_custom_tags.py`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_account_statement_import_mt940' или през CLI:
odoo -i l10n_bg_account_statement_import_mt940 -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)
- Модулни тестове: `tests/`

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
