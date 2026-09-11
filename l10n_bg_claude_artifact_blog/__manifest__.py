# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Claude Artifacts to Blog (Odoo Snippets)",
    "version": "19.0.1.0.0",
    "development_status": "Alpha",
    "category": "Website/Website",
    "summary": (
        "Collect Claude artifacts and publish them as blog posts built from "
        "native Odoo website snippets."
    ),
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., Odoo Community Association (OCA)",
    "maintainers": ["rosen-vladimirov"],
    "website": (
        "https://github.com/rosenvladimirov/l10n-bulgaria/tree/19.0/"
        "l10n_bg_claude_artifact_blog"
    ),
    "license": "LGPL-3",
    "depends": [
        "website_blog",
    ],
    "external_dependencies": {"python": ["lxml"]},
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/claude_snippet_rule_data.xml",
        "views/snippet_templates.xml",
        "views/claude_artifact_views.xml",
        "views/claude_artifact_block_views.xml",
        "views/claude_snippet_rule_views.xml",
        "wizards/claude_artifact_import_wizard_views.xml",
        "wizards/claude_artifact_publish_wizard_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_bg_claude_artifact_blog/static/src/scss/artifact_content.scss",
        ],
    },
    "installable": True,
    "application": False,
}
