# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MT940 Raiffeisen Bank Bulgaria Format Bank Statements Import',
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov '
              'Prodax Ltd., '
              'Odoo Community Association (OCA)',
    'website': 'https://www.openerp.bg',
    'category': 'Banking addons',
    'depends': [
        'account_bank_statement_import_mt940_base',
        ],
    'data': [
        'views/view_account_bank_statement_import.xml',
        ],
    'demo': [
        'demo/demo_data.xml'
        ],
    'installable': True,
}
