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
