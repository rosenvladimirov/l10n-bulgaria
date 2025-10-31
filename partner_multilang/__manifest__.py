{
    "name": "Partner Multilang",
    "version": '18.0.1.0.4',
    "license": "AGPL-3",
    "category": "Localization",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/partner-contact",
    "description": """
        Multilang partner names. Transliterate names.
    """,
    "external_dependencies": {
        "python": [
            "transliterate",
            "unidecode",
            "lingua",
        ]
    },
    "depends": [
        "base",
        "contacts",
    ],
    "data": [
        "views/res_lang_views.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "demo": [],
    "installable": True,
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "post_load": "post_load_hook",
}
