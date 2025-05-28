# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Bg Tax Admin',
    'summary': """This is a technical module that adds the necessary functionalities required by Bulgarian legislation.""",
    'version': '18.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'depends': [
        'account',
        'l10n_bg_reports_audit',
        'l10n_bg_config',
        'l10n_bg_tax_offices',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_fiscal_position_tax_action.xml',
        'views/partner.xml'
    ],
    'demo': [
    ],
}
