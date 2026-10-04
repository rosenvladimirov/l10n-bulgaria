Bridge between Point of Sale and the Bulgarian VAT ledger (art. 119 VAT Act,
art. 112 of its regulation).

Every journal entry created when a POS session is closed (and every
reversal created when an order is invoiced after its session is closed)
becomes a sales report (document type 81) for the partner "Random
customer" with UIC 999999999999999 (15 nines, as required by the NRA).
Invoiced orders are already excluded from the session entry by Odoo.

The random customer itself lives in `l10n_bg_config` and is shared with the eShop
(`l10n_bg_website_sale_invoice_request`).
