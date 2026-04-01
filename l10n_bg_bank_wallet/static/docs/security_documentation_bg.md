# Crypto Wallet Security Documentation

## Обзор

Модулът `l10n_bg_crypto_wallet` реализира **трислойна система за сигурност** за управление на криптографски ключове в Odoo 19. Системата комбинира криптографска защита на ниво данни с многостепенен контрол на достъпа, базиран на Odoo security framework.

---

## Съдържание

- [Архитектура на сигурността](#архитектура-на-сигурността)
- [Модели за сигурност](#модели-за-сигурност)
- [Криптографски мерки](#криптографски-мерки)
- [Контрол на достъпа](#контрол-на-достъпа)
- [Файлова система](#файлова-система-и-съхранение)
- [Audit и мониториране](#audit-и-мониториране)
- [Временна сигурност](#временна-сигурност)
- [Multi-Company поддръжка](#multi-company-support)
- [Обработка на грешки](#error-handling-и-recovery)
- [Performance](#performance-и-scalability)
- [Препоръки](#препоръки-за-използване)

---

## Архитектура на сигурността

### Трислойна защита
```

┌─────────────────────────────────────────────────────────────┐
│                    Слой 3: Application Logic                │
│  • Програмни проверки в Python                              │
│  • Temporal permissions                                     │
│  • Audit trail и logging                                    │
├─────────────────────────────────────────────────────────────┤
│                    Слой 2: Odoo Security                    │
│  • Access Control Lists (ACL)                               │
│  • Record Rules                                             │
│  • Security Groups                                          │
├─────────────────────────────────────────────────────────────┤
│                    Слой 1: Криптография                     │
│  • AES-256 шифроване (Fernet)                               │
│  • PBKDF2 key derivation                                    │
│  • Индивидуални salt стойности                              │
│  • Защитени файлове (600 permissions)                       │
└─────────────────────────────────────────────────────────────┘
```
---

## Модели за сигурност

### Security Groups
```

group_crypto_wallet_admin
├── group_crypto_wallet_generate
│   └── group_crypto_wallet_write
│       └── group_crypto_wallet_read
└── group_crypto_wallet_export
    └── group_crypto_wallet_read
```
| Група | Права | Наследява |
|----------|----------|--------------|
| `read` | Четене на портфейли | - |
| `write` | Четене + Писане | read |
| `generate` | Генериране на ключове | write |
| `export` | Експортиране | read |
| `admin` | Пълни административни права | generate + export |

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

- Потребителите виждат само собствените си портфейли

#### Admin All Access
```xml
<field name="domain_force">[(1, '=', 1)]</field>
```

- Администраторите имат достъп до всички портфейли

#### Company Isolation
```xml
<field name="domain_force">[
    '|',
    ('user_id.company_ids', 'in', user.company_ids.ids),
    ('user_id.company_id', '=', user.company_id.id)
]</field>
```

- Изолация на данни между компании

---

## Криптографски мерки

### Алгоритми за шифроване

| Компонент | Алгоритъм | Параметри |
|--------------|--------------|--------------|
| **Symmetric Encryption** | AES-256-GCM (Fernet) | 256-bit ключ |
| **Key Derivation** | PBKDF2-HMAC-SHA256 | 100,000 итерации |
| **Salt Generation** | Random | 16 bytes |
| **Encoding** | Base64 URL-safe | - |

### Процес на шифроване

```python
# 1. Генериране на salt
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

# 3. Шифроване
f = Fernet(key)
encrypted_data = f.encrypt(json.dumps(wallet_data).encode())
```

---

## Заключение

Модулът `l10n_bg_crypto_wallet` реализира **robust система за сигурност**, която комбинира:

- **Криптографска защита** на ниво данни с industry-standard алгоритми
- **Многостепенен access control** чрез Odoo security framework
- **Гъвкави разрешения** с temporal и company-based ограничения
- **Comprehensive audit trail** за проследяване на операциите
- **Recovery механизми** за обработка на грешки
- **Performance optimizations** за scalability

---

*Последно обновяване: 2026-04-01*
*Версия на документацията: 1.1*
*Модул версия: 19.0.1.0.0*
