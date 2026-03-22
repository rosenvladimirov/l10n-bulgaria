This module integrates Odoo with the
[InfoPay](https://integration.infopay.bg/) online banking API for
Bulgarian banks.

It provides headless (no-GUI) methods for:

* **Downloading bank statements** – fetch booked transactions via the
  InfoPay REST API and create ``account.bank.statement`` records with
  full duplicate-prevention through ``unique_import_id``.
* **Submitting payment orders** – domestic BGN credit transfers, SEPA
  EUR transfers, budget/tax payments and bulk orders (2–250 items).
* **Polling payment status** – track submitted orders until they reach
  a final state (Executed, Rejected, etc.).

The InfoPay access token is stored encrypted in the
``l10n_bg_bank_wallet`` crypto wallet and distributed to each user's
wallet at login time so that credentials are never kept in plain text.
