from . import controllers
from . import models
from . import wizard


# ─── Install-time conflict guard ─────────────────────────────────────
# We provide a Community alternative to the Enterprise `iot` + `pos_iot`
# path for barcode readers / scales. Letting both live in the same DB
# would result in double-dispatch — every scan added twice, every weight
# overwritten twice. Refuse to install if EE is already in.

def _pre_init_check_no_iot(env):
    iot = env["ir.module.module"].search([
        ("name", "in", ("iot", "pos_iot")),
        ("state", "in", ("installed", "to upgrade", "to install")),
    ])
    if iot:
        from odoo.exceptions import UserError
        names = ", ".join(iot.mapped("name"))
        raise UserError(
            "Cannot install `l10n_bg_erp_net_fp` while Enterprise "
            f"module(s) {names} are present — they manage the same "
            "hardware paths (barcode reader, scale, IoT box) as the "
            "proxy bridge in this module. Either:\n\n"
            "  • Uninstall the EE iot module(s) first, then install "
            "this one (uses our Odoo.ErpNet.FP proxy + bus_inject "
            "channel), or\n"
            "  • Keep EE iot and do NOT install this module — the EE "
            "longpoll already handles scans."
        )
