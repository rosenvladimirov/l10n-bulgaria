# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Bg City',
    'summary': """
        This module adds to the database the nomenclature of localities from Bulgaria""",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'depends': [
        'base_address_extended',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_city_types.xml',
        'data/res.country.state.csv',
        'data/res.city.csv',
        'data/city_hall/res.city.csv',
        'data/municipality/res.city.csv',
        'data/settlement/res.city.csv',
        'data/res_country_data.xml',
        'views/res_city_view.xml',
    ],
    'demo': [
    ],
    'post_init_hook': 'post_init_hook',
}
