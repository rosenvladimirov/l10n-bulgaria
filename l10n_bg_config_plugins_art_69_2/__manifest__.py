# Copyright 2025 Rosen Vladimirov
# License OPL-1.0 or later (https://www.odoo.com/documentation/19.0/legal/licenses.html?highlight=odoo%20proprietary%20license%20v1%200#odoo-apps).

{
    'name': 'Bulgaria - a transaction under Article 69, paragraph 2 of the VAT Act',
    'summary': """Configuration plugins for a transaction under Article 69, paragraph 2 of the VAT Act is a supply
    with a place of performance in another EU Member State, without charging Bulgarian VAT,
    reported in box 18 of the VAT return.""",
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations',
    'license': 'OPL-1',
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria-enterprise',
    'depends': [
        'account',
        'l10n_bg_config',
    ],
    'data': [
    ],
    'demo': [
    ],
    'images': [
        'static/description/banner.png',
    ],
    'tags': ['localization', 'accounting', 'bulgaria', 'configuration'],

    # Version requirements
    'odoo_version': '19.0',
    'python_version': '>=3.11',
    'installable': True,
    'countries': ['BG'],
}
