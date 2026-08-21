{
    "name": "Account Payment Order — Restore Partner Bank ACL",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting/Accounting",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "summary": "Give the Contact Creation group back the core access rights "
               "on res.partner.bank and res.bank that account_payment_order "
               "reassigns to its own Payments group.",
    "description": """
Account Payment Order — Restore Partner Bank ACL
================================================

``account_payment_order`` does not add its own access lines for bank data.
Its ``security/ir.model.access.csv`` re-declares two records that belong to
``base`` — ``base.access_res_partner_bank_group_partner_manager`` and
``base.access_res_bank_group_partner_manager`` — and hands them to
``group_account_payment``.

Because an access line has a single group, the effect is not additive: the
rights are moved, not shared. Everybody who holds *Contact Creation* and is
not a payments officer silently loses create/write/unlink on bank accounts
and banks. The failure surfaces far from its cause — most often while
reconciling a bank statement, where Odoo wants to store the counterparty
account and raises "You are not allowed to create records of type Bank
Accounts".

This module restores the two ``base`` records to ``base.group_partner_manager``
with the upstream permission set, and adds *separate* access lines that give
``group_account_payment`` the same full access. Both groups end up with the
rights their own module intends, which is what the OCA module should have
declared in the first place.

It depends on ``account_payment_order`` so the loader always applies it after
the module it corrects, and auto-installs wherever that module is present.
""",
    "depends": ["account_payment_order"],
    "data": ["security/ir.model.access.csv"],
    "auto_install": True,
    "installable": True,
}
