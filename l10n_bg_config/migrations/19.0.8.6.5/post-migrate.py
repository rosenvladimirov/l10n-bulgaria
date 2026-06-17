# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later.
"""При надстройка: направи registration пинг веднага (без да се чака cron-а).

post_init_hook прави пинга при инсталация; при -u той не се пуска, затова
тук пингваме на всяка надстройка до тази версия.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("[l10n_bg_config] %s: registration пинг при надстройка", version)
    try:
        env["res.company"]._l10n_bg_push_registration()
    except Exception:
        _logger.exception("[l10n_bg_config] registration пинг при надстройка пропадна")
