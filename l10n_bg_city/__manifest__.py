# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Bulgarian City's, villages and municipalities",
    "description": """
        This module adds to the database the nomenclature of localities from Bulgaria""",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "depends": [
        "base_address_extended",
        "contacts",
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
