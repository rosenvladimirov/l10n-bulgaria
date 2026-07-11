# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'CFX Traffic Monitor — Live Spreadsheet Dashboard',
    'summary': """
        Real-time Spreadsheet Dashboard for CFX shop-floor traffic
        (cfx.machine.stat) with a live-refresh bridge that re-evaluates
        the pivots/list the moment a new CFX message arrives.""",
    'description': """
Excel-like Spreadsheet Dashboard over ``cfx.machine.stat`` that refreshes
in REAL TIME.

Odoo Spreadsheet dashboards load their pivot/list data once, on open, and
never auto-refresh. This module adds a bridge ("плъг"):

- ``cfx.machine.stat`` broadcasts a lightweight bus signal on every create
  (channel ``cfx_dashboard``) and also fires the per-user
  ``l10n_bg_live_refresh`` ``list`` signal (live cfx.machine.stat list views).
- A tiny always-on backend service turns the broadcast into an ``env.bus``
  event ``CFX_STAT_NEW``.
- An OWL patch on the EE ``SpreadsheetDashboardAction`` (in the lazy
  ``spreadsheet.o_spreadsheet`` bundle) listens for ``CFX_STAT_NEW`` and,
  debounced, dispatches ``REFRESH_ALL_DATA_SOURCES`` on the active
  dashboard model — the pivots and list re-evaluate without a page reload.

Dashboard content (group "CFX Monitoring", one published dashboard):
- Pivot: message count by machine_kind x message_name.
- Pivot: quantity + defects by event_time (per day) x machine_kind.
- List: latest CFX messages (handle, message, work order, time, quantity).
    """,
    'version': '19.0.1.2.0',
    'author': 'Rosen Vladimirov',
    'license': 'AGPL-3',
    'category': 'Manufacturing/IoT',
    'depends': [
        'l10n_bg_erp_net_fp_plugin_cfx',
        'l10n_bg_live_refresh',
        'spreadsheet_dashboard',
    ],
    'data': [
        'data/cfx_dashboard.xml',
    ],
    'assets': {
        # Постоянна backend услуга: bus channel -> env.bus "CFX_STAT_NEW".
        'web.assets_backend': [
            'l10n_bg_erp_net_fp_cfx_dashboard/static/src/js/cfx_dashboard_bus.js',
        ],
        # Мостът живее в мързеливо зареждания o_spreadsheet bundle, където
        # е дефиниран SpreadsheetDashboardAction (НЕ в assets_backend).
        'spreadsheet.o_spreadsheet': [
            'l10n_bg_erp_net_fp_cfx_dashboard/static/src/bundle/cfx_dashboard_bridge.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
