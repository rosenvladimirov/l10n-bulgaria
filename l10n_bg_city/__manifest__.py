# Copyright 2023 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Bulgarian City's, villages and municipalities",
    "description": """
    This module adds the nomenclature of localities from Bulgaria
    """,
    "version": "17.0.1.0.1",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "base_address_extended",
        "contacts",
        "l10n_bg_multilang",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/res_city_types.xml",
        "data/res_country_data.xml",
        "views/res_city_view.xml",
    ],
    "demo": [],
    "post_init_hook": "post_init_hook",
}
