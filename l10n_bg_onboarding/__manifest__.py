# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Bulgarian Localization Onboarding",
    "version": "19.0.1.0.1",
    "summary": "Full-screen animated guided setup shown on first login of "
    "a freshly created Bulgarian database",
    "description": """
A distinctive, full-screen, narrative onboarding experience that runs
the Bulgarian localization step-by-step installation on first login.

Folk-modernist editorial visual direction (ink & rose, cross-stitch
motifs), Lottie-driven chapter animations with an animated-SVG fallback.

Augments — does not replace — the in-Settings modal stepper. Reuses the
existing l10n_bg_config engine (l10n.bg.vertical / .step / wizard); no
business logic duplicated.
""",
    "category": "Localization",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": ["l10n_bg_config", "web"],
    "auto_install": ["l10n_bg_config"],
    "data": [
        "data/onboarding_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_onboarding/static/src/onboarding/scene_engine.js",
            "l10n_bg_onboarding/static/src/onboarding/chapters.js",
            "l10n_bg_onboarding/static/src/onboarding/onboarding_action.js",
            "l10n_bg_onboarding/static/src/onboarding/onboarding_action.xml",
            "l10n_bg_onboarding/static/src/onboarding/onboarding.scss",
        ],
    },
    "installable": True,
}
