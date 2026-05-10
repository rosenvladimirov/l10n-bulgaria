# InfoPay Integration (l10n_bg_infopay)

> **Current version:** 18.0.4.1.0 · **License:** LGPL-3 · **Status:** core
> module of the БГ InfoPay subsystem.  See `CHANGELOG.md` for the full
> version history.

`l10n_bg_infopay` is the **core configuration + shared helpers** for
all Borica InfoPay PSD2 integration in Odoo 18.  By itself it gives
you the full single-company workflow (statement sync, invoice
issuance, single + bulk payment submission, status polling) on the
journals of the active company.  Multi-framework integration
(`account.payment.order`, `account.batch.payment`, OdooFin
synchronisation widgets) is delivered through small **bridge
modules** which depend on this one.

## Module layout

```
l10n_bg_infopay/                      ← THIS MODULE (core)
├── infopay.provider                    raw HTTP client (session,
│                                       accounts, transactions, payments)
├── res.company                         credentials (user + admin token)
├── account.journal                     per-IBAN config + statement sync
├── account.payment                     single + bulk submit + polling
├── account.move                        InfoPay invoice issuance
├── l10n.bg.infopay.statement.mixin     abstract mixin (consumed by
│                                       bridge modules)
└── l10n.bg.infopay.payment.mixin       abstract mixin (consumed by
                                        bridge modules)

l10n_bg_infopay_oca_statement       ← bridge: OCA online.bank.statement.provider
l10n_bg_infopay_oca_payment         ← bridge: OCA account.payment.order
l10n_bg_infopay_ee_statement        ← bridge: EE  account.online.account
l10n_bg_infopay_ee_payment          ← bridge: EE  account.batch.payment
l10n_bg_infopay_ui                  ← shared: wallet-unlock wizard + buttons
```

## What this module gives you

* **Encrypted credentials** — user wallet (password-protected via
  `l10n_bg_bank_wallet`) for write operations + admin Fernet-encrypted
  token for cron read operations.  Two-key model so unattended sync
  doesn't need a stored wallet password.
* **Bank statement sync** — `journal._l10n_bg_infopay_pull_transactions(date_from, date_to)`
  fetches & deduplicates statement lines, ready for reconciliation.
* **Single payments** — BGN domestic, SEPA EUR, BGN budget (НАП).
  Returns `paymentId` + `scaRedirect` URL for SCA.
* **Bulk payments** — 2..250 items via the bulk endpoints.
* **Status polling** — single + bulk `/payments/{id}/status`.
* **Invoice issuance** — `/api/invoices` for InfoPay payment-collection
  links (this is **NOT** the regulated `e-faktura.bg`).

## What's NEW in 18.0.4.x

* **18.0.4.1.0** — registers three new `account.payment.method`
  records (`l10n_bg_infopay_domestic_bgn`, `_sepa_eur`, `_budget_bgn`)
  consumed by the OCA + EE payment bridges.
* **18.0.4.0.0** — **breaking** field rename: every field this module
  adds to a public Odoo model now carries the `l10n_bg_` prefix
  (`infopay_unique_id` → `l10n_bg_infopay_unique_id`, etc.).
  Pre-migration script does the eight `ALTER TABLE RENAME COLUMN`
  operations idempotently; existing data is preserved.

## Installation

```bash
pip install requests cryptography
git clone <l10n-bulgaria>
git clone <l10n-bulgaria-expert>   # optional: brings the OCA bridges
git clone <l10n-bulgaria-ee>       # optional: brings the EE bridges
```

`-i l10n_bg_infopay` to install just the core; bridges will auto-install
when their host frameworks (`account_payment_order`, `account_online_synchronization`,
`account_batch_payment`) are present.

## Configuration

1. Open **Settings → Companies → InfoPay**.
2. Paste the `Unique ID` from your Borica registration confirmation.
3. Enter the **user token** in your wallet (the password-protected
   wallet provided by `l10n_bg_bank_wallet`).
4. Enter the **admin token** — gets Fernet-encrypted into
   `ir.config_parameter` for unattended cron use.
5. On each bank journal, set the **InfoPay account UUID** that maps
   to that journal's IBAN.  The discovery wizard
   (`l10n_bg_infopay_ui` module) can populate this for you.

## License

LGPL-3 — see https://www.gnu.org/licenses/lgpl

## Author

Rosen Vladimirov, Odoo Community Association (OCA).
