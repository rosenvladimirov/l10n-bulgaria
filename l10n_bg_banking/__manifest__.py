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
    """,
    'author': 'Rosen Vladimirov, Deyan Lyubenov',
    'license': 'OEEL-1',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria-ee',
    'depends': ["base", "account", "account_bank_statement_import"],
    'data': [
        'security/ir.model.access.csv',
        'views/res_bank_views.xml',
        'views/menu_items.xml',
    ],
}
