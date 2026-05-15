# Copyright 2024 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Bg Tax Offices",
    "summary": """
        Bulgarian tax offices, NSSI regional directorates, and NSI bureaus as partners""",
    "version": "19.0.1.1.0",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "l10n_bg",
        "l10n_bg_city",
    ],
    "data": [
        "data/res_tax_offices.xml",
        "data/res_noi_offices.xml",
        "data/res_nsi_offices.xml",
    ],
    "demo": [],
}
