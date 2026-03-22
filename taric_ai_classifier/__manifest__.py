# -*- coding: utf-8 -*-
{
    'name': 'AI TARIC & INTRASTAT Classifier',
    'version': '18.0.2.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'AI-powered automatic TARIC and INTRASTAT code classification for products',
    'description': """
AI TARIC & INTRASTAT Code Classifier
=====================================

Automatic product classification with TARIC and INTRASTAT codes using AI.

Features
--------
* Automatic TARIC code suggestions through AI product analysis
* Integration with official EU TARIC database
* INTRASTAT nomenclature for Bulgaria
* Classification audit history
* Batch classification of multiple products
* Code verification against official portals
* Automatic supplementary units population
* Support for Bulgarian and English

Technical Details
-----------------
* Claude AI (Anthropic) for intelligent recognition
* TARIC API integration
* Combined Nomenclature database
* Bulgarian NSI INTRASTAT compliance requirements

Configuration
-------------
1. Go to Settings > General Settings > TARIC AI Configuration
2. Enter your Anthropic API key
3. Configure classification preferences
4. Start classifying products!

Usage
-----
* Individual product classification: Product form > Action > Classify with AI
* Batch classification: Product list view > Action > Batch Classify
* View classification history: Product form > Classification History smart button
    """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'stock_delivery',
        'account',
        'ai_agent_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/taric_code_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/batch_classify_wizard_views.xml',
    ],
    'demo': [],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
