{
    "name": "Markdown Viewer Locale",
    "version": "18.0.3.0.9",
    "license": "LGPL-3",
    "category": "Tools",
    "summary": "View localized Markdown files based on user language",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            # CSS
            "markdown_viewer_locale/static/src/css/markdown_popup.css",
            # XML templates - реактивирани (2026-07-05): Knowledge Share VList
            # конфликтът (2026-04-30) е потвърдено работещо и на други инсталации
            # (Solid 55, 19.0) със същия form_controller.xml/markdown_popup.js —
            # тук версията вече е по-чиста (lazy-load на marked/highlight, без
            # debug логове), затова е реактивирана. Ако проблемът се повтори,
            # проверявай конкретно Knowledge Share VList, не този модул.
            ('after', 'web/static/src/views/form/form_controller.xml',
             'markdown_viewer_locale/static/src/xml/form_controller.xml'),
            # JS - регистър + FormController patch
            'markdown_viewer_locale/static/src/js/markdown_registry.js',
            ('after', 'web/static/src/views/form/form_controller.js',
             'markdown_viewer_locale/static/src/js/markdown_popup.js'),
        ],
        # marked.js + highlight.js се товарят lazy през loadJS при първо отваряне
        # на popup-а — преди бяха в assets_backend и замърсяваха всеки backend page.
    },
    'images': [
        'static/description/banner.png',
    ],
    "installable": True,
    "application": False,
}
