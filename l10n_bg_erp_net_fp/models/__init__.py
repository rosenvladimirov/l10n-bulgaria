from . import erp_net_fp
from . import fiscal_printer_response
from . import fiscal_priters_status
from . import fiscal_priters_status_history
from . import pos_config
from . import pos_order
from . import account_tax_group
from . import pos_printer
from . import pos_session
from . import erp_net_fp_exceptions
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

# Native iot.box / iot.device bridge AND packaging weight QC (Phase 3)
# both moved to bridge module `l10n_bg_erp_net_fp_iot` (in l10n-bulgaria-ee,
# auto_install=True) in 18.0.10.1.0 so the core stays Community-installable.
# Packaging QC depends on iot.device for the scale read, so it ships
# only on EE-bridge installs.
from . import barcode_rule_extensions
from . import barcode_rule_target
