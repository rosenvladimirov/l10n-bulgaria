# Changelog — payment_mypos

All notable changes to this module. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/). The v18 and v19
branches share the same feature line; version numbers differ only by
the Odoo series prefix, and v19 carries one extra entry (1.4.0) for the
Odoo 19 hook port that has no v18 equivalent.

## [2.0.0] — 2026-05-15

### Added
- **IPCRefund flow (Bundle 2).** Server-to-server refunds via the myPOS
  IPCRefund method, mirroring `IPC/Refund.php` from the official PHP SDK.
  - `payment.provider._mypos_build_refund_payload` — ordered POST fields.
  - `payment.provider._mypos_send_refund` — signs, POSTs (`requests`,
    `OutputFormat=json` since the SDK Helper rejects `post`), then
    verifies the response signature with the same RSA primitive as
    notification verification.
  - `payment.transaction._send_refund_request` override + shared
    `_mypos_do_refund` driver.
  - New non-secret provider fields `mypos_application_id` /
    `mypos_partner_id` (mandatory for refund/void under v1.4.1).
- 7 refund tests (`tests/test_refund_flow.py`) with `requests.post`
  mocked — payload order, AUP guards, success/declined paths, and a
  post-sign tamper that must fail response-signature verification.

### Security
- **AUP — refund only to original card.** `_mypos_build_refund_payload`
  refuses to build a refund whose source transaction has no
  `provider_reference` (IPC_Trnref). myPOS additionally enforces this
  gateway-side, so funds can only ever return to the original card.

## [1.3.0] — 2026-05-15

### Added
- **Wallet-backed partner API credentials.** clientId / clientSecret
  live in the company-owner's `crypto.wallet` (hard dep on
  `l10n_bg_bank_wallet`), encrypted with the owner's bcrypt password
  hash — cron jobs sudo-ing to the owner can read them without a
  session password. Mirrors the InfoPay 6.0.0 pattern.
  - Helpers: `_mypos_get_client_credentials`,
    `_mypos_set_client_credentials`, `_mypos_has_client_credentials`.
  - `mypos.load.credentials.wizard` — paste the JSON produced by
    `tools/mypos_browser credentials --integration-id N`, or type the
    pair manually; restricted to `base.group_system`.

### Fixed
- Test fixture populates `payment_method_id` (Odoo 18 added a NOT NULL
  constraint that errored every notification test).

## [1.2.0] — 2026-05-15

### Fixed
- **HTTPS enforced on `URL_Notify`.** myPOS reverses transactions whose
  notify URL isn't SSL-enabled (Integration Checklist requirement).
  `_mypos_get_return_url` now raises in production state on a non-HTTPS
  `web.base.url`, and warns (test mode only).

### Changed
- Manifest description pinned to **Checkout API v1.4.1** (matches the
  Partner Portal Resources tab).

## [1.1.0] — 2026-05-14

### Fixed
- **Cancel-flow signature regression.** The controller injected
  `Status="cancel"` *before* signature verification, so every cancel
  callback failed. The gateway already signs `Status`; the tamper was
  removed.
- **PII log redaction.** `pprint.pformat(data)` could log callback
  fields including `Card.maskedPAN` / `Card.brand` / `Card.expiry`
  (PCI-DSS-restricted even when masked). Added `_LOG_SAFE_KEYS`
  allowlist + `_redact_for_log`.
- **Status 20 (DUPLICATE_TRANSMISSION) idempotent.** myPOS retries
  notify when it doesn't get `OK`; the old code hit the unknown-status
  branch and flipped the tx to error. Now a no-op.
- **IPC_Trnref captured** into `provider_reference` on first success —
  required for downstream refund/void.

### Added
- `_MYPOS_STATUS` — 27-code map mirroring `Defines.php`. Errors now read
  `status 9 (wrong_amount)` instead of `unknown status 9`.
- 6 notification integration tests (`tests/test_notification_flow.py`).

## [1.0.0] — 2026-05-XX

### Added
- Initial release. myPOS Checkout API IPCPurchase redirect flow with
  3D Secure, RSA-SHA256 (PKCS#1 v1.5) request signing byte-identical to
  the official PHP SDK, signature-verified IPN handling, signing-layer
  test suite.

---

## v19-only entry

### [1.4.0] — 2026-05-15 (19.0 branch only)

#### Fixed
- **Ported notification handling to the Odoo 19 hook surface.** Odoo 19
  renamed `_process_notification_data` → `_apply_updates` and
  `_get_tx_from_notification_data` → `_extract_reference` /
  `_search_by_reference`. The v19 mirror was still calling the old
  super(), so every notification test threw `AttributeError`. v18 keeps
  the old names (that's what Odoo 18 expects); the two branches now
  diverge at the notification surface but share the signature layer.
