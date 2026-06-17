# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later.
"""Re-пинг с поправена EE детекция (брои и 'to upgrade' модули)."""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_DEFAULT_URL = "https://www.odoo-shell.dev"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env["ir.config_parameter"].sudo()
    if not (ICP.get_param("l10n_bg.register_server_url") or "").strip():
        ICP.set_param("l10n_bg.register_server_url", _DEFAULT_URL)
    if not ICP.get_param("l10n_bg.register_enabled"):
        ICP.set_param("l10n_bg.register_enabled", "1")

    ee = env["res.company"]._l10n_bg_ee_modules()
    _logger.info("[l10n_bg_config] 8.6.7: EE детекция=%s", ee)
    try:
        res = env["res.company"]._l10n_bg_push_registration()
        _logger.info("[l10n_bg_config] 8.6.7: пинг резултат=%s", res)
    except Exception:
        _logger.exception("[l10n_bg_config] 8.6.7: пинг пропадна")
