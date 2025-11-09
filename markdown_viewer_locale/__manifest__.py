{
    "name": "Markdown Viewer Locale",
    "version": "18.0.3.0.4",
    "license": "LGPL-3",
    "category": "Tools",
    "summary": "View localized Markdown files based on user language",
    "author": "Your Company Name",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            # Библиотеки
            "markdown_viewer_locale/static/src/lib/marked.min.js",
            "markdown_viewer_locale/static/src/lib/highlight.min.js",
            # CSS
            "markdown_viewer_locale/static/src/css/markdown_popup.css",
            # XML templates - СЛЕД form_controller.xml
            ('after', 'web/static/src/views/form/form_controller.xml',
             'markdown_viewer_locale/static/src/xml/form_controller.xml'),
            # JS - ПЪРВО регистъра, после патча
            'markdown_viewer_locale/static/src/js/markdown_registry.js',
            ('after', 'web/static/src/views/form/form_controller.js',
             'markdown_viewer_locale/static/src/js/markdown_popup.js'),
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    "installable": True,
    "application": False,
}
