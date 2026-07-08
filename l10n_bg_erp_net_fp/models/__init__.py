from . import erp_net_fp
from . import pos_config
from . import pos_order
from . import account_tax_group
from . import pos_printer
from . import pos_session
from . import res_config_settings
from . import res_users

# Proxy-aware extensions (Odoo.ErpNet.FP Python proxy support).
# All ADD-only — none of these change existing behaviour.
from . import fiscal_printer_device_extensions
from . import fiscal_printer_device_external
from . import fiscal_frame_log
from . import fiscal_session
from . import fiscal_plu
from . import fiscal_plu_device_line
from . import fiscal_z_report
from . import pos_config_extensions
from . import product_template_extensions
from . import product_product_extensions
from . import product_pricelist_extensions
from . import pos_payment_method_extensions
from . import pos_order_extensions
from . import pos_session_external

# External Shift dashboard (independent of pos.session) — 18.0.12.0.0
from . import fiscal_shift
from . import fiscal_shift_receipt

# barcode.rule routing targets moved to `l10n_bg_erp_net_reader`
# (in 19.0.16.0.0) заедно с reader сервиза — reader concern, POS-free.

# BlueCash shift-close sync service — engine for upserting receipts /
# refunds / cash movements. Driver-agnostic (called by shift_bridge_client
# в новата архитектура; преди беше callванo от deprecated shift_close
# HTTP controller).
from . import shift_sync_service

# Shift bridge HTTP client — Odoo → proxy → Android (port 9103 NDJSON).
# Backs cron + pos_session_signal hooks.
from . import shift_bridge_client

# pos.session signal hooks — emit shift.open / shift.close.request
# през shift_bridge_client.
from . import pos_session_signal

# BlueCash storno Phase 2 (anchor_bluecash_storno_phase2_contract)
from . import pos_order_storno_service
