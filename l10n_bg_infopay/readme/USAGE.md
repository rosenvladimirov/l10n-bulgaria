### Initial setup

```python
# 1. Store InfoPay credentials (run once as admin)
company = env.user.company_id
company._infopay_set_credentials(
    unique_id='<your-infopay-uuid>',
    access_token='<your-infopay-token>',
)

# 2. Discover bank accounts and match to journals by IBAN
journal = env['account.journal'].browse(journal_id)
journal._infopay_discover_accounts()
```

### Fetching bank statements

```python
# Sync a single journal (last 30 days or since last sync)
journal._infopay_sync_statements()

# Sync with explicit date range
from datetime import date
journal._infopay_sync_statements(
    date_from=date(2025, 1, 1),
    date_to=date(2025, 1, 31),
)

# Sync all InfoPay-enabled journals at once
env['account.journal']._infopay_sync_all_statements()
```

### Submitting payment orders

```python
payment = env['account.payment'].browse(payment_id)

# Single domestic BGN payment
payment._infopay_submit()

# Single SEPA EUR payment (auto-detected by currency)
payment._infopay_submit()

# Budget / tax payment
payment._infopay_submit_budget(
    ultimate_debtor='Ivan Ivanov',
    tax_payer_id='8407088414',
    tax_payer_type='EGN',
)

# Bulk payment (2–250 items, same journal & currency)
payments._infopay_submit_bulk()
```

### Polling payment status

```python
# Check one payment
payment._infopay_check_status()

# Check & handle all pending payments
env['account.payment']._infopay_pull_all_pending()
```

All methods that submit payments return an ``ScaRedirect`` URL that the
user must open in a browser to complete bank-level Strong Customer
Authentication (SCA).
