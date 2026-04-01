This module provides a secure encrypted wallet for storing sensitive
data needed by banking integrations:

* RSA private/public keys for digital signing
* API keys and access tokens
* Passwords and certificates
* SSH keys, PGP keys, and other cryptographic material

All data is encrypted at rest using **PBKDF2** key derivation
(100 000 iterations, SHA-256) and **Fernet** symmetric encryption
(AES-256-GCM). Each user has an isolated wallet encrypted with their
own Odoo password hash, so keys are only accessible after
authentication.
