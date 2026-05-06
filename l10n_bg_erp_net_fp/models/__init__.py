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

# Proxy-aware extensions (Odoo.ErpNet.FP Python proxy support).
# All ADD-only — none of these change existing behaviour.
from . import fiscal_printer_device_extensions
from . import fiscal_frame_log
from . import fiscal_session
from . import pos_config_extensions
from . import product_template_extensions
from . import pos_payment_method_extensions
from . import pos_order_extensions

# Native Odoo IoT Box integration (18.0.9.0.0+).
# Adds connection_mode to iot.box, action_via_proxy to iot.device,
# and a generic iot.device.response table for browser-proxied flows.
# Backward-compatible: existing fiscal.printer.device flow untouched.
from . import iot_device_response
from . import iot_box_extensions
from . import iot_device_extensions

# Packaging weight QC (18.0.10.0.0+).
# Abstract weighable mixin + MO/picking integration. Reads scale via
# iot.device.read_weight() (Phase 2), compares to BoM expected weight
# ± tolerance %, marks records as pass/fail.
from . import packaging_weighable_mixin
from . import res_company_packaging_qc
from . import mrp_packaging_qc
from . import stock_picking_packaging_qc
