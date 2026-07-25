# Copyright 2024 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Bg Assets',
    'description': """
        Add rules for tax desperation base Bulgarian law.""",
    'version': '16.0.1.0.0',
    'license': 'OEEL-1',
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria-ee',
    'depends': [
        'account_asset',
        # 'l10n_bg_config',
        # 'account_asset_product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/asset_report_base.xml',
        'data/asset_report.xml',
        'data/account_report_actions.xml',
        'data/menuitems.xml',
        'views/account_asset_views.xml',
    ],
    'demo': [
    ],
}
