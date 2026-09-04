# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later.
"""Гарантира register_server_url + enabled (data е noupdate=1 и не се налага
при -u на вече инсталиран модул) и пингва веднага. С подробно логване."""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_DEFAULT_URL = "https://www.odoo-shell.dev"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env["ir.config_parameter"].sudo()

    url = (ICP.get_param("l10n_bg.register_server_url") or "").strip()
    _logger.info("[l10n_bg_config] 8.6.6: текущ server_url=%r", url)
    if not url:
        ICP.set_param("l10n_bg.register_server_url", _DEFAULT_URL)
        _logger.info("[l10n_bg_config] 8.6.6: зададен server_url=%s", _DEFAULT_URL)
    if not ICP.get_param("l10n_bg.register_enabled"):
        ICP.set_param("l10n_bg.register_enabled", "1")

    main = env.ref("base.main_company", raise_if_not_found=False) \
        or env["res.company"].search([], order="id", limit=1)
    _logger.info(
        "[l10n_bg_config] 8.6.6: главна фирма=%s vat=%r",
        main.name if main else None, main.vat if main else None,
    )
    try:
        res = env["res.company"]._l10n_bg_push_registration()
        _logger.info("[l10n_bg_config] 8.6.6: пинг резултат=%s", res)
    except Exception:
        _logger.exception("[l10n_bg_config] 8.6.6: пинг пропадна")
