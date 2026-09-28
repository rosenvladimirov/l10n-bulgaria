**Version 19.0.2.1.0**

- Search by partner name uses the trigram index: the case-folded expression
  `lower(<unaccent>(x) COLLATE "und-x-icu")` is the same in the query and in the
  new `*_pm_fold` indexes (measured on PostgreSQL 17, `C` locale, 200 000 partners:
  0.84 ms instead of 240 ms full scan).
- Name search across all translations is one SQL condition instead of one
  `search()` per field and language.
- `complete_name_multilanguage` gets a trigram index (`index=True` is ignored by
  the core for translated fields, so it had none).
- Lists are ordered by the translated name in the user's language with its ICU
  collation, backed by a btree index per active language (`*_pm_order`).
- `models/base.py` was never imported; it is replaced and registered.
- Tests: `tests/test_multilang_search.py`.

**Version 18.0.1.0.4**

- Automatic language detection using lingua and langdetect libraries
- Multi-language search with JSONB support
- Automatic sorting by user's language in list and kanban views
- Support for Bulgarian, Russian, Serbian, Macedonian, Ukrainian, and Belarusian
- Mixin architecture for easy extension to custom models

**Background:**

The Cyrillic alphabet does not use Latin letters, which creates problems with ordering in list and kanban views. Bulgarian law requires names of people, companies, cities, and streets to be transliterated to Latin letters using ISO 9.

In previous Odoo versions, `display_name` was not translatable. Version 16.0 introduced computed fields with multilingual capability, but only for reports, not the interface.

This module aims to solve the problem for languages using different character sets by providing automatic transliteration and proper multi-language support.
