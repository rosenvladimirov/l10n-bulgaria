{
    "name": "Markdown Viewer Locale",
    "version": "18.0.1.0.1",
    "license": "LGPL-3",
    "category": "Tools",
    "summary": "View localized Markdown files based on user language",
    "description": """
Markdown Viewer with Localization Support
==========================================

This module provides functionality to view Markdown files with automatic
language localization based on user preferences.

Features:
---------
* Display Markdown content in popup dialogs
* Automatic language detection based on user settings
* Syntax highlighting support
* Clean and responsive UI

Technical:
----------
* Uses marked.js for Markdown rendering
* Integrated highlight.js for code syntax highlighting
* Supports multiple languages through locale-specific files
    """,
    "author": "Your Company Name",
    "website": "https://github.com/yourusername/your-repo",
    "depends": ["web"],
    "data": [
        "views/markdown_snippet.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "https://cdn.jsdelivr.net/npm/marked/marked.min.js",
            "https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js",
            "markdown_viewer_locale/static/src/js/markdown_popup.js",
            "markdown_viewer_locale/static/src/css/markdown_popup.css",
        ],
        "web.assets_qweb": [
            "markdown_viewer_locale/static/src/xml/markdown_popup.xml",
        ],
    },
    "installable": True,
    "application": False,
}
