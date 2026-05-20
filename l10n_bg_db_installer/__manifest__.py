# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Bulgarian Database Installer",
    "version": "19.0.1.0.3",
    "summary": "Bulgaria fields on the database manager + guided "
    "localization setup on a freshly created database",
    "description": """
Adds two fields (VAT/UIC and KID codes) to the Odoo database manager
create form. When a database is created with country = Bulgaria, the
values are written onto the new company (vat, l10n_bg_kid_codes) and the
guided Localization Installer (l10n_bg_config stepper) is presented to
the administrator on first login via a configuration step.

Thin module — reuses the existing l10n_bg_config installer; no business
logic duplicated.
""",
    "category": "Localization",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": ["l10n_bg_config"],
    "auto_install": ["l10n_bg_config"],
    "data": [
        "data/l10n_bg_db_installer_data.xml",
    ],
    "installable": True,
}
