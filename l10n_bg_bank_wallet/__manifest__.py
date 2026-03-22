# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': 'Bulgarian Banking Integration - Crypto Wallet',
    'version': '18.0.1.0.2',
    'category': 'Localization',
    'summary': 'Secure storage of cryptographic keys and passwords for banking integrations',
    'description': """
Crypto Wallet for Sensitive Data Storage
=========================================

This module provides a secure way to store:
* RSA keys for digital signing
* API keys for banking integrations
* Passwords and certificates
* Other sensitive cryptographic data

Uses PBKDF2 with 100,000 iterations and Fernet symmetric encryption.

Features:
---------
* **Secure Storage**: All data is encrypted using industry-standard cryptography
* **User Isolation**: Each user has their own wallet accessible only to them
* **Key Management**: Add, retrieve, and manage different types of keys
* **Banking Ready**: Designed specifically for banking API integrations
* **Audit Trail**: Track when keys are accessed and modified

Security:
---------
* Uses user password hash as master password
* PBKDF2 key derivation with 100,000 iterations
* Fernet symmetric encryption for data protection
* Per-user salt for additional security

Supported Key Types:
-------------------
* RSA Private/Public Keys
* API Keys (for banking APIs)
* SSH Keys
* PGP Keys
* Passwords
* Certificates
* Tokens
* Custom data types
    """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/OCA/l10n-bulgaria',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/l10n_bg_crypto_wallet.xml',
        'security/ir.model.access.csv',
        'views/l10n_bg_crypto_wallet.xml',
        'wizards/crypto_wallet_add_key_wizard.xml',
        'wizards/crypto_wallet_unlock_wizard.xml',
        'wizards/crypto_wallet_change_password_wizard.xml',
        'wizards/crypto_wallet_export_wizard.xml',
        'wizards/crypto_wallet_key_manager_wizard.xml',
        'wizards/crypto_wallet_generate_keypair_wizard.xml',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'external_dependencies': {
        'python': ['cryptography'],
    },
    'maintainers': ['rosenvladimirov'],
    'development_status': 'Beta',
}
