# Changelog

## 18.0.1.0.2 (2026-05-02)

- Drop the non-standard `#. UI / settings labels` separator comments from `i18n/bg.po`. Odoo's translation loader (`tools/translate.py`) treats `#.` lines as reference comments and runs them through a regex that requires a `module:` prefix; arbitrary text raised `AttributeError: 'NoneType' object has no attribute 'groups'` and aborted the install.

## 18.0.1.0.1 (2026-05-02)

- `disposable_email_domains` Python package downgraded from `external_dependencies` to a soft import inside `_refresh_from_package`. The module installs and runs without the package; the offline blocklist fallback simply does not work until the admin runs `pip install disposable_email_domains` on the server.

## 18.0.1.0.0 (2026-05-02)

- Initial release.
- Mandatory email verification between Step 1 and Step 2 of `/shop/register`.
- Per-company configurable method: `disabled` / `link` / `otp` / `both`.
- OTP: SHA-256 hashed at rest, `secrets.randbelow` generation, configurable length (4–8), expiry, max attempts, resend cooldown. Constant-time compare via `hmac.compare_digest`.
- Verification link: `secrets.token_urlsafe(32)`, single-use, same expiry as OTP.
- Disposable email blocklist with weekly refresh from Kickbox upstream and `disposable_email_domains` Python package fallback.
- Seed list of ~50 most common temp providers shipped with the module (`source="seed"`).
- `disposable.email.domain` model uses `tools.ormcache` on the active set; cache invalidated on create/write/unlink.
- Subdomain-attack protection: every dotted suffix of the registrant's domain is checked against the blocklist (e.g. `foo.mailinator.com` is rejected).
- Punycode IDN handling: domains are converted to ASCII before lookup.
- Post-init hook marks all pre-existing `res.users` records as `email_verified=True` so an upgrade does not lock anyone out.
- Admin UI: Settings page section under **Website**, **Email Verification** page on the user form (Force Verify / Reset Verification buttons), Disposable Email Domains list view under Users menu.
- Bulgarian translation in `i18n/bg.po`.
- Tests: `test_disposable_check.py`, `test_otp_flow.py`, `test_link_flow.py` covering hashing-only persistence, attempts/lockout, expiry, cooldown, cache invalidation, subdomain attacks, IDN.
