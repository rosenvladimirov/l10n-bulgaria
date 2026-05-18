# Bulgarian Database Installer (`l10n_bg_db_installer`)

Thin module. Adds two fields — **VAT / UIC** and **KID codes** — to the
Odoo database manager *create database* form. When a database is created
with **Country = Bulgaria**:

1. Odoo auto-installs `l10n_bg` (BG localization) → `l10n_bg_config`
   auto-installs (`auto_install=['l10n_bg']`) → this module
   auto-installs (`auto_install=['l10n_bg_config']`).
2. The controller writes the captured values onto the new company:
   `res.company.vat` (EIK/VAT) and `res.company.l10n_bg_kid_codes`
   (KID free-text; resolved by the existing bootstrap when the chart of
   accounts is loaded).
3. An `ir.actions.todo` configuration step opens the guided
   **Localization Installer** stepper (`l10n_bg_config`
   `l10n.bg.vertical.wizard`) for the administrator on first login.
   The V0 *Fetch from Trade Register* step uses `company.vat`.

No business logic is duplicated — the module only wires the existing
`l10n_bg_config` installer to the new-database flow.

## ⚠️ Operational note (must read before deploy)

`/web/database/manager` is a **nodb** page. Its template is rendered
with `qweb_render` (standalone), so normal module view inheritance does
**not** apply there — the form is extended by overriding the `web`
`Database` controller and post-processing the HTML with lxml (the same
technique Odoo core itself uses in `web/controllers/database.py`).

For the controller override to be active on the nodb manager page, the
module's controllers must be loaded at server start. Depending on the
Odoo build this means the module should be present in the addons path
**and** — if controller activation on the nodb routing map proves
build-specific — added to `server_wide_modules` in `odoo.conf`
(e.g. `server_wide_modules = base,web,l10n_bg_db_installer`) followed by
a server restart. **This must be dev-verified on a 19.0 instance.**

This module changes only the *new database* flow. Existing databases
(their DB already exists) are unaffected; the guided installer remains
reachable inside any BG database via Settings → Localization Installer.

## TODO / verify on dev-19

- `ir.actions.todo` auto-presentation on first admin login in a freshly
  created BG DB (the v17+ config-step chain is less used; confirm it
  fires; fallbacks: admin Home Action or an OWL one-shot).
- nodb controller activation (see operational note).
- 18.0 port after 19.0 dev-verify.
