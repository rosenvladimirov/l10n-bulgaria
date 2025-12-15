This module provides technical infrastructure for automatic transliteration of partner names, addresses, and company information.

**Legal Requirements:**

Countries using Cyrillic letters (Bulgaria, Russia, Serbia, Macedonia, Ukraine, Belarus) have legal requirements for transliteration to Latin in official documents.

**Sorting Problems:**

Non-Latin scripts create sorting issues in list and kanban views. For example, Cyrillic "Г" and Latin "G" are positioned differently, leading to confusion.

**Technical Limitations:**

In Odoo versions before 16.0, `display_name` was not translatable. Version 16.0 introduced computed fields with multi-language support, but only for reports.

This module solves these problems by providing automatic transliteration, multi-language search, and proper sorting.
