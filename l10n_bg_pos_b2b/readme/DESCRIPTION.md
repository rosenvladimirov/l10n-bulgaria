Wholesale (B2B) sales in the same Point of Sale session.

* A **Wholesale** button above the products switches the current order to
  wholesale and shows a block with the business customer: company ID,
  VAT number, representative, address, pricelist, payment terms and credit
  (limit, used, overdue), plus the invoice details that are missing.
* **Business customers are always invoiced** (VAT Act, Art. 113, para. 1):
  companies, sole traders, legal entities without VAT registration and
  partners marked "Always Invoice". The "Invoice" option is locked for
  them, and the order cannot be paid without it.
* **Checks before payment** (never at synchronisation): incomplete invoice
  details (warn or block), foreign or intra-EU customer (back office
  invoice), pricelist in a foreign currency, credit limit (warn or block)
  and a credit cap while offline.
* **Two dates on the invoice**: the issue date is the day the invoice is
  actually created; the delivery date (tax event) is the date of the order.
  An order paid offline and synchronised the next day gets a correct issue
  date.
* **One order, one invoice**: repeated synchronisation or a back-office
  "Invoice" never create a second invoice.
* **Safety net on the server**: a paid order of a business customer that
  reaches the server without "Invoice" is invoiced anyway, with a note in
  the chatter. If the invoice cannot be posted during synchronisation, the
  order stays paid and appears in *Wholesale Orders without Invoice*.

The module does not depend on a fiscal device. The fiscal receipt for
wholesale sales is handled by `l10n_bg_erp_net_fp_pos_b2b`.

Specification: `specs/pos-b2b-wholesale/ANCHOR.md`.
