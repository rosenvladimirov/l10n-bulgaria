{
    "name": "Bulgarian Invoices — No Lots & Serials Table",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting/Localizations",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "summary": "Drop the core SN/LN table from invoices issued by Bulgarian "
               "companies, without touching invoices of companies in other "
               "countries.",
    "description": """
Bulgarian Invoices — No Lots & Serials Table
============================================

``stock_account`` appends a Product / Quantity / SN/LN table to the invoice
report. Its only guard is the group *Display Serial & Lot Number on Invoices*
(``stock_account.group_lot_on_invoice``), and a group is global: switching the
Inventory setting off removes the table from every company in the database.

That is the wrong granularity for a multi-country database. A Bulgarian
invoice carries no lot numbers, while the Greek and Cypriot companies in the
same database do print them. Worse, the group can also be held per user, so
the same invoice comes out with the table for one colleague and without it for
another.

This module keys the table on the issuing company's country instead: the whole
block, including the empty ``oe_structure`` filler underneath it, is skipped
when the company is Bulgarian. Nothing else changes, and companies outside
Bulgaria keep the core behaviour and the core setting.
""",
    "depends": ["stock_account"],
    "data": ["views/report_invoice.xml"],
    "installable": True,
}
