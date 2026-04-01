### Storing a key

```python
wallet = env['crypto.wallet'].get_user_wallet_or_create()
wallet.add_key_with_user_password('my_api_key', 'api_key', 'secret-value')
```

### Retrieving a key

```python
wallet = env['crypto.wallet'].get_user_wallet()
key_data = wallet.get_key_with_user_password('my_api_key')
print(key_data['data'])  # → 'secret-value'
```

### Quick access helpers

```python
CW = env['crypto.wallet']
CW.quick_store('token', 'api_key', 'abc123')
data = CW.quick_access('token')
```

### Generating an RSA or EC keypair

```python
wallet.generate_keypair('signing', key_type='rsa')
# creates signing_private and signing_public in the wallet
```
