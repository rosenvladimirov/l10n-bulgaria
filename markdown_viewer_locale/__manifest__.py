{
    "name": "Markdown Viewer Locale",
    "version": "18.0.3.0.8",
    "license": "LGPL-3",
    "category": "Tools",
    "summary": "View localized Markdown files based on user language",
    "author": "Your Company Name",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            # CSS
            "markdown_viewer_locale/static/src/css/markdown_popup.css",
            # XML templates временно изключени за изолация на Knowledge Share VList
            # breakage (2026-04-30). Без бутона popup-ът не се отваря, но JS patch-ът
            # остава да се регистрира — ако Share работи без XML, потвърдено е, че
            # template inheritance е cause-ът.
            # ('after', 'web/static/src/views/form/form_controller.xml',
            #  'markdown_viewer_locale/static/src/xml/form_controller.xml'),
            # JS - регистърът остава за да не се счупят import-ите на dependents
            # (mrp_bom_for_lot, project_management_logikal). markdown_popup.js
            # с FormController patch-а е изключен за изолация (2026-04-30).
            'markdown_viewer_locale/static/src/js/markdown_registry.js',
            # ('after', 'web/static/src/views/form/form_controller.js',
            #  'markdown_viewer_locale/static/src/js/markdown_popup.js'),
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
