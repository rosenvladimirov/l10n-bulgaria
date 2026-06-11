# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "AI Pipeline (Skills + Injection Engine)",
    "version": "19.0.1.1.0",
    "development_status": "Alpha",
    "category": "Technical",
    "summary": (
        "Pipeline stack with Anthropic-style Skills: progressive disclosure, "
        "semantic matching, dynamic step injection on top of AI Tokenizer."
    ),
    "author": "Rosen Vladimirov, BL Consulting, Odoo Community Association (OCA)",
    "maintainers": ["rosen-vladimirov"],
    "website": (
        "https://github.com/rosenvladimirov/l10n-bulgaria/tree/19.0/"
        "l10n_bg_ai_pipeline"
    ),
    "license": "AGPL-3",
    "depends": [
        "l10n_bg_claude_terminal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ai_model_views.xml",
        "views/ai_skill_views.xml",
        "views/ai_pipeline_step_views.xml",
        "views/ai_pipeline_run_views.xml",
        "views/menu.xml",
        "data/ai_model_data.xml",
        "data/pipeline_steps.xml",
    ],
    "installable": True,
    "application": False,
}
