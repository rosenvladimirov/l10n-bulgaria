# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Statement Import Mt940",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "depends": ["account_statement_import_file"],
    "data": [
        "wizard/account_statement_import.xml",
    ],
    "external_dependencies": {"python": ["mt-940"]},
    "demo": [],
}
