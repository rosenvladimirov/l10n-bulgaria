# -*- coding: utf-8 -*-
{
    'name': 'AI TARIC & INTRASTAT Classifier',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localization',
    'summary': 'AI-powered automatic classification of TARIC and INTRASTAT codes',
    'description': """
AI TARIC & INTRASTAT Code Classifier
=====================================

Автоматична класификация на стоки със TARIC и INTRASTAT кодове използвайки AI.

Възможности:
------------
* Автоматично предлагане на TARIC кодове чрез AI анализ на продукта
* Интеграция с официалната TARIC база данни на ЕС
* INTRASTAT номенклатура за България
* История на класификации за одит
* Batch класификация на множество продукти наведнъж
* Верификация на кодове спрямо официалните портали
* Автоматично попълване на допълнителни единици (supplementary units)
* Подръжка на български и английски език

Технологии:
-----------
* Claude AI (Anthropic) за интелигентно разпознаване
* TARIC API integration
* Combined Nomenclature database
* Bulgarian NSI INTRASTAT requirements
    """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'account',
        'l10n_bg',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/taric_data.xml',
        'views/product_views.xml',
        'views/taric_code_views.xml',
        'views/intrastat_code_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/batch_classify_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
