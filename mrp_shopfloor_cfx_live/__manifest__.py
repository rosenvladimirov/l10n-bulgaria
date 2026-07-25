# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Shop Floor — CFX Live (real-time machine progress)',
    'summary': """
        Real-time injection of live CFX-IPC machine progress into the
        Enterprise Shop Floor (mrp_display). Additive OWL layer: reloads
        the matching Manufacturing/Work Order card on a CFX bus event and
        shows an ephemeral live badge (placed count / station state).""",
    'description': """
Shop Floor CFX Live
===================

A thin, additive frontend layer that makes the Enterprise Shop Floor
(``mrp_workorder`` OWL client action ``mrp_display``) react in real time to
CFX-IPC machine events forwarded by the ErpNet.FP proxy.

CFX events travel over the existing ``erpnet_fp_proxy_events`` bus channel
(see ``l10n_bg_erp_net_fp_plugin_cfx`` / ``l10n_bg_erp_net_fp_bus_inject``);
``l10n_bg_live_refresh`` already fans every proxy envelope out as a single
``PROXY_EVENT`` on ``env.bus``. This module simply subscribes to that event,
filters for the ``cfx.*`` type vocabulary and:

* **Repaint (authoritative):** patches ``MrpDisplay.setup`` — on a matching
  CFX event it calls ``env.reload(record)`` (the Shop Floor repaint lever,
  ``mrp_display.js``), pulling authoritative DB state (``qty_produced`` etc.).
  The standard ``l10n_bg_live_refresh`` Form/List controller patches do NOT
  cover the custom ``mrp_display`` client action, so this bridge is required
  for the tablet board.
* **Ephemeral overlay (no DB round-trip):** patches ``MrpDisplayRecord`` and
  ``t-inherit`` its template to add a transient live badge (placed component
  count / station state / last CFX message) fed straight from the bus event.

No fork/edit of ``mrp_workorder`` or ``l10n_bg_live_refresh`` — everything is
done via ``@web/core/utils/patch`` and template ``t-inherit``.
    """,
    'version': '19.0.1.0.0',
    'author': 'Rosen Vladimirov, Terraros Commerce Ltd.',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'license': 'AGPL-3',
    'category': 'Manufacturing',
    'depends': [
        'mrp_workorder',
        'l10n_bg_live_refresh',
        'bus',
    ],
    'assets': {
        'web.assets_backend': [
            'mrp_shopfloor_cfx_live/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
