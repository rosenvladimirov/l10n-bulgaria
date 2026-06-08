# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Task Multilang',
    'summary': """Add multilingual support for project task fields in Bulgarian localization""",
    'description': """
Bulgarian Project Multilingual Support
=====================================

This module extends the project management functionality to provide multilingual
support for project task fields in Bulgarian localization.

Features:
---------
* Multilingual support for project task names and descriptions
* Integration with partner multilingual capabilities
* Bulgarian localization compliance
* OCA community standards compliance

Technical Details:
-----------------
* Extends project.task model with multilingual field support
* Integrates with partner_multilang module for consistent translation handling
* Follows Bulgarian localization standards (l10n_bg)

Installation:
------------
This module requires the 'project' and 'partner_multilang' modules to be installed.

Usage:
------
After installation, project task fields will support multiple languages,
allowing Bulgarian companies to manage projects in both Bulgarian and other languages.

    """,
    'version': '19.4.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov',
    'maintainer': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Localization',
    'depends': [
        'project',
        'partner_multilang',
    ],
    'data': [
        # View файлове ще бъдат добавени когато са готови
    ],
    'demo': [],
    'assets': {},
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'external_dependencies': {
        'python': [],
    },
    'development_status': 'Production/Stable',
    'maintainers': ['rosenvladimirov'],
    'support': 'https://github.com/rosenvladimirov/l10n-bulgaria/issues',
    'countries': ['BG'],
}
