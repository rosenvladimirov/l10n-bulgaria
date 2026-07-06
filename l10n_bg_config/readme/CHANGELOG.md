# Changelog

## 19.0.8.6.10

- Фикс: shortcut-ът Alt+Shift+K за генериране на API ключ на партньор не работеше —
  view-то `view_res_partner_form_api_key` (закача `js_class=api_key_res_partner_form`)
  беше `active=False` (изключено при v18→v19 порта). Върнато на `active=True`.
- Фикс: `form_view.js` — `_t` с template literal (`_t(\`…${result}\`)`) заменено с
  правилния паттерн `_t("… %s", result)` (иначе преводимо-невалидно + ESLint грешка).

## 19.0.8.6.9

- Фикс: премахнато дублираното видимо поле за номер на документа на формата на
  движението. `l10n_bg_name` (related алиас на `l10n_bg_document_number`) вече е
  invisible в групата „Bulgarian VAT"; видимото поле остава единствено
  `l10n_bg_document_number` (етикет „Document Number", от `l10n_bg_reports_config`).

## 19.0.6.2.0

- Blacklist mechanism: encrypted `data/blacklist.enc` (Fernet) with VAT-based lookup
- Controller `/l10n_bg/blacklist/check` — decrypts file using key from `ir.config_parameter`
- OWL service `l10n_bg_blacklist`: sticky warning notification for blacklisted companies,
  non-dismissable overlay when security file is missing or corrupted
- `post_migrate_hook` for upgrade compatibility from older versions
- CLI tool `tools/update_blacklist.py` for managing the encrypted blacklist file
- External dependency: `cryptography` (Fernet encryption)
