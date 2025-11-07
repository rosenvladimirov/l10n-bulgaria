
{
    'name': 'Markdown Viewer Locale Dropdown',
    'version': '7.0',
    'category': 'Tools',
    'summary': 'View localized Markdown files with dropdown for language and document selection',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'markdown_viewer_locale_dropdown/static/lib/marked.min.js',
            'markdown_viewer_locale_dropdown/static/lib/highlight.min.js',
            'markdown_viewer_locale_dropdown/static/src/js/markdown_popup.js',
            'markdown_viewer_locale_dropdown/static/src/css/markdown_popup.css',
        ],
        'web.assets_qweb': [
            'markdown_viewer_locale_dropdown/static/src/xml/markdown_popup.xml',
        ],
    },
    'data': [
        'views/markdown_snippet.xml',
    ],
    'installable': True,
    'application': False,
}
