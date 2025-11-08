{
    'name': 'Markdown Viewer Locale',
    'version': '5.0',
    'category': 'Tools',
    'summary': 'View localized Markdown files based on user language',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
            'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js',
            'markdown_viewer_locale/static/src/js/markdown_popup.js',
            'markdown_viewer_locale/static/src/css/markdown_popup.css',
        ],
        'web.assets_qweb': [
            'markdown_viewer_locale/static/src/xml/markdown_popup.xml',
        ],
    },
    'data': [
        'views/markdown_snippet.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
