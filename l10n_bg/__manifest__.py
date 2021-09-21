# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Bulgaria - Accounting",
    "version": "11.0.5.1",
    "author": "Rosen Vladimirov",
    'category': 'Localization',
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "description": """
This is the module to manage the Accounting Chart, VAT structure, Fiscal Position and Tax Mapping.
==================================================================================================

Bulgarian accounting chart and localization.
    """,
    'depends': [
        'account',
        'account_tax_fixes',
        'base_vat',
        'base_iban',
        'base_address_city',
        #'account_financial_report',
        'account_tax_unece',
        'account_tag_menu',
        'sale',
    ],
    'external_dependencies': {'python': ['xlrd']},
    "demo": [],
    "data": [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/l10_bg_chart_data_init.xml',
        'data/l10_bg_chart_data.xml',
        'data/res_city_types.xml',
        'data/res_country_data.xml',
        'data/account_tax_data.xml',
        'data/account_fiscal_position_data.xml',
        'data/account_chart_template.yml',
        'data/res.country.state.csv',
        'data/res.bank.csv',
        'data/res.city.csv',
        'data/municipality/res.city.csv',
        'data/city_hall/res.city.csv',
        'data/settlement/res.city.csv',
        'data/l10n_bg_chard_data_update.xml', # fix special account configurations
        'views/res_partner_views.xml',
        'views/res_company_view.xml',
        'views/account_view.xml',
        'views/account_invoice_view.xml',
        'views/account_journal_view.xml',
        'views/res_city_views.xml',
        'wizards/account_invoice_refund_view.xml',
    ],
    'post_init_hook': '_preserve_tag_on_taxes',
    "license": "AGPL-3",
    "installable": True,
}
