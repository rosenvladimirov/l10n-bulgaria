# Changelog

All notable changes to the l10n_bg_sale_order_delivery_note module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.1.1.1] - 2026-04-10

### Fixed
- XPath за вмъкване на top comments в `report_saleorder_document` използваше несъществуващ селектор `//table[@id='main_table']`. В стандартния Odoo 18 sale шаблон таблицата няма `id`, само клас `o_main_table`. Заменено с `//table[hasclass('o_main_table')]`. Бъгът блокираше upgrade на модула.

## [18.0.1.0.0] - 2026-03-01

### Added
- Initial changelog entry
