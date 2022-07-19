# -*- coding: utf-8 -*-
# Copyright 2009-2018 dXFactory.
# Copyright 2009-2018 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Bulgaria - Intrastat Product Declaration',
    'version': '11.0.3.0.0',
    'category': 'Intrastat',
    'license': 'AGPL-3',
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    'summary': 'Intrastat Product Declaration for Bulgaria',
    'author': "Rosen Vladimirov <vladimirov.rosen@gmail.com>, "
              "dXFactory Ltd. <http://www.dxfactory.eu>, "
              "Noviat",
    'depends': [
        'intrastat_product',
        'intrastat_product_picking_package',
        'l10n_bg',
        'l10n_bg_extend',
        ],
    'conflicts': [
        'base',
        'l10n_bg_intrastat',
        'report_intrastat',
        ],
    'data': [
        'security/intrastat_security.xml',
        'security/ir.model.access.csv',
        'data/intrastat_unit.xml',
        'data/intrastat_transaction.xml',
        'data/intrastat_region.xml',
        #'views/account_invoice.xml',
        'views/product_views.xml',
        'views/res_config_settings.xml',
        'views/l10n_bg_intrastat_product.xml',
        'views/intrastat_installer.xml',
        'views/res_city_views.xml',
        'data/res.city.csv',
    ],
    'installable': True,
}
