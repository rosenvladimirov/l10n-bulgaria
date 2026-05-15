# Markdown Viewer (Locale-aware)

> Renders localized Markdown files (README.bg.md vs README.en.md /
> README.md) based on the user's language — used to show the right
> per-module documentation inside Odoo.

**Module:** `markdown_viewer_locale` | **Version:** 18.0.3.0.8 | **License:** LGPL-3 | **Category:** Localization

## Overview

Every localization module ships `README.en.md` + `README.bg.md` (and
some `README.md`). This utility picks and renders the variant matching
the logged-in user's language, so a Bulgarian user sees the Bulgarian
documentation and an English user sees English — inside the Odoo UI,
not just on GitHub.

## What it does

Selects the locale-appropriate Markdown file (`*.bg.md` for `bg_BG`,
falling back to `*.en.md` / `*.md`) and renders it.

## Status note (2026-04-30)

A `FormController` JS patch that opened the viewer in a popup caused a
breakage and was **disabled for isolation**. Without the button the
popup doesn't auto-open; the locale-selection rendering logic itself
is intact. Re-enabling requires restoring the FormController patch (see
the comments in `static/`).

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `web` | (utility — used across the localization) |

## Configuration

None. Install — localized README rendering follows the user language.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Documents every module's `README.en.md` / `README.bg.md`
