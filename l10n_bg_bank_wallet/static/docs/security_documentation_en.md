# Crypto Wallet Security Documentation

## Overview

The `l10n_bg_crypto_wallet` module implements a **three-layer security system** for cryptographic key management in Odoo 19. The system combines data-level cryptographic protection with multi-tier access control based on the Odoo security framework.

---

## Table of Contents

- [Security Architecture](#security-architecture)
- [Security Models](#security-models)
- [Cryptographic Measures](#cryptographic-measures)
- [Access Control](#access-control)
- [File System](#file-system-and-storage)
- [Audit and Monitoring](#audit-and-monitoring)
- [Multi-Company Support](#multi-company-support)
- [Error Handling](#error-handling-and-recovery)
- [Performance](#performance-and-scalability)
- [Recommendations](#usage-recommendations)

---

## Security Architecture

### Three-Layer Protection
```

┌─────────────────────────────────────────────────────────────┐
│                    Layer 3: Application Logic               │
│  • Python programmatic checks                               │
│  • Temporal permissions                                     │
│  • Audit trail and logging                                  │
├─────────────────────────────────────────────────────────────┤
│                    Layer 2: Odoo Security                   │
│  • Access Control Lists (ACL)                               │
│  • Record Rules                                             │
│  • Security Groups                                          │
├─────────────────────────────────────────────────────────────┤
│                    Layer 1: Cryptography                    │
│  • AES-256 encryption (Fernet)                              │
│  • PBKDF2 key derivation                                    │
│  • Individual salt values                                   │
│  • Protected files (600 permissions)                        │
└─────────────────────────────────────────────────────────────┘
```
---

## Security Models

### Security Groups
```

group_crypto_wallet_admin
├── group_crypto_wallet_generate
│   └── group_crypto_wallet_write
│       └── group_crypto_wallet_read
└── group_crypto_wallet_export
    └── group_crypto_wallet_read
```
| Group | Rights | Inherits |
|----------|-----------|-------------|
| `read` | Read wallets | - |
| `write` | Read + Write | read |
| `generate` | Generate keys | write |
| `export` | Export functionality | read |
| `admin` | Full administrative rights | generate + export |

### Model Access Rights

| Group\Operation | Read | Write | Create | Delete |
|-------------------|---------|----------|-----------|-----------|
| **read** | Yes | No | No | No |
| **write** | Yes | Yes | Yes | No |
| **generate** | Yes | Yes | Yes | No |
| **export** | Yes | No | No | No |
| **admin** | Yes | Yes | Yes | Yes |

### Record Rules

#### User Own Records
```xml
<field name="domain_force">[('user_id', '=', user.id)]</field>
```
- Users only see their own wallets

#### Admin All Access
```xml
<field name="domain_force">[(1, '=', 1)]</field>
```

- Administrators have access to all wallets

#### Company Isolation
```xml
<field name="domain_force">[
    '|',
    ('user_id.company_ids', 'in', user.company_ids.ids),
    ('user_id.company_id', '=', user.company_id.id)
]</field>
```

- Data isolation between companies

---

## Cryptographic Measures

### Encryption Algorithms

| Component | Algorithm | Parameters |
|--------------|--------------|---------------|
| **Symmetric Encryption** | AES-256-GCM (Fernet) | 256-bit key |
| **Key Derivation** | PBKDF2-HMAC-SHA256 | 100,000 iterations |
| **Salt Generation** | Random | 16 bytes |
| **Encoding** | Base64 URL-safe | - |

### Encryption Process

```python
# 1. Generate salt
salt = os.urandom(16)

# 2. Key derivation
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
    backend=default_backend()
)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

# 3. Encryption
f = Fernet(key)
encrypted_data = f.encrypt(json.dumps(wallet_data).encode())
```

---

## Conclusion

The `l10n_bg_crypto_wallet` module implements a **robust security system** that combines:

- **Cryptographic protection** at data level with industry-standard algorithms
- **Multi-tier access control** through Odoo security framework
- **Flexible permissions** with temporal and company-based restrictions
- **Comprehensive audit trail** for operation tracking
- **Recovery mechanisms** for error handling
- **Performance optimizations** for scalability

---

*Last updated: 2026-04-01*
*Documentation version: 1.1*
*Module version: 19.0.1.0.0*
