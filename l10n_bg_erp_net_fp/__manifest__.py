
# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': 'ErpNet.FP Fiscal Printer for odoo',
    'summary': """
        Integration with ERP.BG fiscal printers through ErpNet.FP server.
        Supports real-time fiscal receipt printing and status monitoring.""",
    'description': """
This module provides integration between Odoo POS and fiscal printers
supported by ErpNet.FP server. Features include:

* Real-time fiscal receipt printing from POS
* Direct browser-to-printer communication for receipts
* Backend support for Z/X reports and administrative operations
* Printer status monitoring
* Automatic fallback to standard printing on error
* Multiple printer support
* Background printer status updates
* Detailed error logging
* Support for different printer models
* Bulgarian tax group mapping (А, Б, В, Г)
* Dual connection mode: Direct (server) and Proxy (browser)
""",
    'version': '18.0.12.0.0',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Point Of Sale',
    "development_status": "Production/Stable",
    'maintainers': ['rosenvladimirov'],
    # Version-bump notes:
    #   18.0.9.0.0  → added `iot` (EE) hard dep for native IoT Box flow
    #   18.0.10.0.0 → added `mrp` + `stock` deps for packaging weight QC
    #   18.0.10.1.0 → REMOVED `iot`, `mrp`, `stock` hard deps — IoT bridge
    #                 + packaging QC moved to `l10n_bg_erp_net_fp_iot`
    #                 (l10n-bulgaria-ee repo, auto_install=True). Core
    #                 stays Community-installable with no IoT/MRP needs.
    #   18.0.10.3.0 → External POS mode Phase 1 — `l10n.bg.fiscal.plu`
    #                 model + consistency check + sync from pricelist +
    #                 stale triggers (product/pricelist write) + two
    #                 wizards (allocate from products, top-N best-sellers).
    #                 Skeleton for Phase 2 (POS open push) and Phase 3
    #                 (POS close Z-import) — toggle on pos.config still
    #                 has no behaviour wired beyond the constraint.
    #   18.0.11.0.0 → External POS mode Phase 2 — POS session open hook
    #                 orchestrates push to device (fiscal.session open +
    #                 VAT groups + operators + PLU table from registry +
    #                 logo + header/footer + X-report sanity). Push
    #                 status surfaced on session form with retry button.
    #                 Manual "Push to device" button on PLU list/form.
    #                 Phase 3 (close-time Z + sales import) still TODO.
    #   18.0.11.1.0 → External POS mode Phase 3 — POS session close hook
    #                 pulls journal from device, imports receipts as
    #                 pos.order records (PLU→product reverse lookup,
    #                 dedupe by FP/<n>), triggers Z (auto_z_on_close),
    #                 closes fiscal.session with z_number + total +
    #                 discrepancy. Adds force-close button (closed_partial
    #                 state) for offline-device scenarios. New field
    #                 pos.payment.method.l10n_bg_external_kind for
    #                 cash/card/voucher mapping.
    #   18.0.11.2.0 → External POS mode Phase 4 — resilience: daily cron
    #                 23:55 auto-close stuck fiscal sessions (Н-18 ≤24h);
    #                 Z-report retry x3 on transient errors (paper-out,
    #                 timeout); pre-push capacity guard (plu_capacity vs
    #                 active PLUs); mid-shift stale warning at close.
    #                 fiscal.session inherits mail.thread/activity for
    #                 alert posting; mail.activity_data_warning fallback
    #                 for managers when auto-Z fails.
    #   18.0.11.3.0 → External POS mode Phase 4.5 — multi-device support:
    #                 new pos.config.l10n_bg_extra_fiscal_printer_ids M2m
    #                 + computed l10n_bg_all_fiscal_devices union; push
    #                 and close orchestrators iterate all devices, one
    #                 fiscal.session per device per pos.session;
    #                 pos.session.l10n_bg_fiscal_session_ids (O2m) with
    #                 backward-compat computed primary alias; receipts
    #                 dedupe key now includes device id (FP/D<id>/<n>);
    #                 force-close handles all open fiscal sessions.
    #   18.0.11.4.0 → External POS mode Phase 5 — UX polish:
    #                 POS UI Navbar badge "External mode" (JS+OWL patch)
    #                 with click-to-show push status notification;
    #                 mid-shift X-report wizard with inline JSON preview
    #                 (multi-device dropdown, running total parsing);
    #                 Grafana dashboard JSON (receipts/h, Z duration,
    #                 discrepancy histogram, top PLUs); README operator
    #                 guide in Bulgarian (setup + daily ops + troubleshoot).
    'depends': [
        'base',
        'bus',
        'mail',
        'point_of_sale',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fiscal_printer_device_cron.xml',
        'data/proxy_sequences.xml',
        'views/fiscal_printer_device_views.xml',
        'views/fiscal_printer_device_proxy_views.xml',
        'views/fiscal_session_views.xml',
        'views/fiscal_frame_log_views.xml',
        'views/pos_config_view.xml',
        'views/pos_config_proxy_views.xml',
        'views/pos_printer_views.xml',
        'views/pos_session_view.xml',
        'views/pos_order_view.xml',
        'views/account_tax_views.xml',
        'views/fiscal_printer_response_views.xml',
        'views/product_template_proxy_views.xml',
        'views/pos_payment_method_proxy_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/menu_items.xml',
        'views/grafana_views.xml',
        'views/grafana_settings_views.xml',
        'views/menu_items_proxy.xml',
        'views/fiscal_plu_views.xml',
        'wizard/fiscal_cash_operation_wizard_view.xml',
        'wizard/plu_allocate_wizard_view.xml',
        'wizard/plu_push_wizard_view.xml',
        'wizard/plu_topn_wizard_view.xml',
        'wizard/x_report_wizard_view.xml',
    ],
    'demo': [
    ],
    'assets': {
        # Backend assets (само за backend, БЕЗ POS зависимости)
        'web.assets_backend': [
            'l10n_bg_erp_net_fp/static/src/js/fiscal_printer_service.js',
            'l10n_bg_erp_net_fp/static/src/js/printer_status_updates.js',
            'l10n_bg_erp_net_fp/static/src/js/printer_id_field.js',
            'l10n_bg_erp_net_fp/static/src/xml/printer_id_field.xml',
            'l10n_bg_erp_net_fp/static/src/js/fiscal_browser_proxy_action.js',
            # 18.0.10.1.0 — Grafana embed dashboard
            'l10n_bg_erp_net_fp/static/src/js/grafana_dashboard.js',
            'l10n_bg_erp_net_fp/static/src/xml/grafana_dashboard.xml',
        ],
        # POS assets (само за POS)
        'point_of_sale._assets_pos': [
            'l10n_bg_erp_net_fp/static/src/js/erp_net_fp_printer.js',
            'l10n_bg_erp_net_fp/static/src/js/pos_printer_service.js',
            'l10n_bg_erp_net_fp/static/src/js/payment_screen.js',
            'l10n_bg_erp_net_fp/static/src/js/payment_screen_pinpad.js',
            'l10n_bg_erp_net_fp/static/src/js/close_pos_popup_patch.js',
            'l10n_bg_erp_net_fp/static/src/xml/pos_close_popup_template.xml',
            'l10n_bg_erp_net_fp/static/src/js/cash_move_popup.js',
            'l10n_bg_erp_net_fp/static/src/js/opening_control_popup_fiscal.js',
            # Phase 5 — external POS mode badge in Navbar
            'l10n_bg_erp_net_fp/static/src/js/external_pos_badge.js',
            'l10n_bg_erp_net_fp/static/src/xml/external_pos_badge.xml',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
