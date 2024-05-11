# Copyright 2024 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n Bg Tax Offices",
    "summary": """
        Add in partners tax offices and department of NRA Bulgaria""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "l10n_bg",
        "l10n_bg_city",
        "l10n_bg_tax_admin",
    ],
    "data": ["data/res_tax_offices.xml"],
    "demo": [],
}
