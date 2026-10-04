Adds an "I want an invoice" switch to the eShop checkout.

Website orders confirmed without it get the random customer (UIC 999999999999999,
from `l10n_bg_config`) as invoice address. A monthly scheduled action invoices all
confirmed orders of the random customer up to the end of the previous month in one
invoice per company, dated the last day of the month and marked as a sales report
(Art. 119 VAT Act, document type 81), so they enter the VAT sales ledger.
