{
    'name': 'L10n BG Banking - Infopay Integration',
    "version": "18.0.0.0.0",
    'category': 'Localization',
    'summary': 'Infopay banking integration for Bulgarian localization',
    'description': """
        Bulgarian Banking Integration with Infopay API

        This module provides integration with Infopay API for importing bank statements
        and transactions from Bulgarian banks through the Infopay platform.

        Features:
        - Session management for secure API communication
        - Simple authentication with Client ID and Access Token
        - Import bank statements and transactions
        - Support for multiple accounts and currencies
        - Connection testing functionality
        - Automatic session lifecycle management

        Dependencies:
        - Python requests module (pip install requests)
        - Odoo base_setup module
        - Odoo account module
        - Odoo account_bank_statement_import module
    """,
    'author': 'Rosen Vladimirov, Deyan Lyubenov',
    'license': 'OEEL-1',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria-ee',
    'depends': ["base", "base_setup", "account"],
    'data': [
        'security/ir.model.access.csv',
        'views/res_bank_views.xml',
        'views/menu_items.xml',
        'views/bank_import_confirmation_wizard_views.xml',
        'views/res_config_settings_views.xml',
    ],
}
