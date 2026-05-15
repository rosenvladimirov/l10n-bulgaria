# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Live Refresh (generic bus-driven view refresh)",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Generic bus channel + OWL patches that live-reload and flash "
               "backend Form/List views when the server changes records",
    "description": """
Live Refresh
============

A small, generic primitive extracted from l10n_bg_claude_terminal.

Server code calls ``env['live.refresh'].notify(model=, res_ids=, mode=)``
(or ``recs._live_refresh_notify()`` via the ``live.refresh.mixin``).  A bus
message is sent to the affected users; a browser-side service forwards it to
patched Form and List controllers, which reload the matching record or list
and briefly flash the changed fields or highlight the new rows.

This module carries no business logic of its own.  It is meant to be a shared
dependency for any module that needs server-driven live UI refresh
(claude terminal, InfoPay payment status, ErpNet.FP fleet, ...).
""",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "license": "AGPL-3",
    "depends": ["web", "bus"],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_live_refresh/static/src/scss/live_refresh.scss",
            "l10n_bg_live_refresh/static/src/js/live_refresh_service.js",
            "l10n_bg_live_refresh/static/src/js/live_refresh_controllers.js",
        ],
    },
    "installable": True,
}
