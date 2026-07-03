# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Bulgaria - KEP Signing (base)",
    "version": "19.4.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Pluggable qualified e-signature (КЕП) backend — choose StampIT "
               "or the local Odoo.ErpNet.FP proxy as the signer",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
}
