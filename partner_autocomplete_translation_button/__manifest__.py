# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Partner Autocomplete — Translation Button",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "category": "Hidden/Tools",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "summary": "Show the translation button on translatable fields that use "
    "the partner autocomplete widget.",
    "depends": ["partner_autocomplete"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "partner_autocomplete_translation_button/static/src/scss/*",
            "partner_autocomplete_translation_button/static/src/xml/*",
        ],
        "web.assets_unit_tests": [
            "partner_autocomplete_translation_button/static/tests/**/*",
        ],
    },
    "installable": True,
    # Дефектът е в шаблона на ядрото и засяга всяко преводимо поле с
    # field_partner_autocomplete — лекът се слага сам заедно с модула-родител.
    "auto_install": True,
    "application": False,
}
